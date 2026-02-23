"""
Agent feature: Chat API route.
"""

import uuid
import os
import json
import asyncio
import time
import urllib.request
import ssl

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from supabase import Client
from langchain_core.messages import HumanMessage, ToolMessage

from app.config import get_settings
from app.core.dependencies import get_db, get_current_user_id
from app.features.agent.graph import get_agent_graph
from app.features.agent.memory import MemoryManager

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    images: list[str] | None = None  # Public URLs from Supabase Storage
    user_location: str | None = None  # Location string for context


class UploadResponse(BaseModel):
    url: str


class ToolResult(BaseModel):
    tool_name: str
    tool_args: dict = {}
    result: str


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_results: list[ToolResult] = []
    tools_used: list[str] = []
    thoughts: str | None = None


@router.post("/upload_image", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Upload an image to Supabase Storage and return its public URL."""
    settings = get_settings()
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Loại file không hỗ trợ: {file.content_type}")

    # Max 10MB
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File quá lớn (tối đa 10MB)")

    # Generate unique filename
    ext = os.path.splitext(file.filename or "image.jpg")[1] or ".jpg"
    filename = f"{user_id}/{uuid.uuid4().hex}{ext}"

    # Upload to Supabase Storage using service key client
    from supabase import create_client
    admin_db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    try:
        admin_db.storage.from_("chat-uploads").upload(
            path=filename,
            file=contents,
            file_options={"content-type": file.content_type},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload thất bại: {str(e)}")

    # Build public URL
    public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/chat-uploads/{filename}"
    return UploadResponse(url=public_url)


def _build_multimodal_content(message: str, image_urls: list[str] | None) -> list[dict] | str:
    """Build multimodal content blocks for LangChain HumanMessage.

    If images are present, returns a list of content blocks.
    Otherwise returns a plain string.
    """
    if not image_urls:
        return message

    content_blocks: list[dict] = []
    for url in image_urls:
        content_blocks.append({"type": "image_url", "image_url": {"url": url}})
    content_blocks.append({"type": "text", "text": message})
    return content_blocks


def _build_db_content(message: str, image_urls: list[str] | None) -> str:
    """Build the content string to save in the database.

    Prepends Markdown image links so the frontend ReactMarkdown
    component can render images automatically.
    """
    if not image_urls:
        return message

    md_images = "\n".join(f"![image]({url})" for url in image_urls)
    return f"{md_images}\n\n{message}"


@router.post("/chat")
async def chat(
    data: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Chat with the AI agent using SSE."""
    memory = MemoryManager(db, user_id)

    # 1. Get or create session
    is_new_session = data.session_id is None
    session = memory.get_or_create_session(data.session_id)
    session_id = session["id"]

    # 2. Load conversation history
    history = memory.load_session_messages(session_id)

    # 3. Apply sliding window
    trimmed_history = memory.apply_sliding_window(history)

    # 4. Add new user message (multimodal if images present)
    human_content = _build_multimodal_content(data.message, data.images)
    trimmed_history.append(HumanMessage(content=human_content))

    # 5. Save user message to DB (Markdown format for UI rendering)
    db_content = _build_db_content(data.message, data.images)
    memory.save_message(session_id, "user", db_content)

    # 5b. Get user location preferences
    default_loc, _ = memory.get_weather_prefs()

    # 6. Prepare state
    state = {
        "messages": trimmed_history,
        "user_id": user_id,
        "user_name": memory.get_user_name(),
        "user_preferences": memory.get_user_preferences(),
        "user_location": data.user_location,
        "default_location": default_loc,
        "conversation_summary": session.get("summary", ""),
    }

    async def generate_chat_stream():
        response_text = ""
        thoughts_text = ""
        tool_results = []
        tool_calls_data = []

        try:
            graph = get_agent_graph()
            async for event in graph.astream_events(
                state,
                version="v2",
                config={"recursion_limit": get_settings().AGENT_RECURSION_LIMIT},
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    content = chunk.content
                    
                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict):
                                if part.get("type") == "thinking":
                                    thinking = part.get("thinking", "")
                                    if thinking:
                                        thoughts_text += thinking
                                        yield f"data: {json.dumps({'type': 'thinking', 'content': thinking})}\n\n"
                                elif part.get("type") == "text":
                                    text = part.get("text", "")
                                    if text:
                                        response_text += text
                                        yield f"data: {json.dumps({'type': 'message', 'content': text})}\n\n"
                    elif isinstance(content, str) and content:
                        response_text += content
                        yield f"data: {json.dumps({'type': 'message', 'content': content})}\n\n"

                elif kind == "on_tool_start":
                    name = event.get("name")
                    yield f"data: {json.dumps({'type': 'tool_call', 'status': 'start', 'name': name})}\n\n"

                elif kind == "on_tool_end":
                    name = event.get("name")
                    data_event = event.get("data", {})
                    output = data_event.get("output")
                    # Extract tool call result
                    result_str = str(output)[:2000] if output else ""
                    yield f"data: {json.dumps({'type': 'tool_call', 'status': 'end', 'name': name, 'result': result_str})}\n\n"
                    
                    tool_calls_data.append({"name": name, "args": {}})
                    tool_results.append(ToolResult(tool_name=name, tool_args={}, result=result_str))

            # 9. Save AI response to DB (include tool_calls for DB record)
            saved_tool_calls = [{"name": tc["name"], "args": tc["args"]} for tc in tool_calls_data] if tool_calls_data else None
            memory.save_message(session_id, "assistant", response_text, saved_tool_calls)

            # 10. Auto-generate session title for new sessions
            if is_new_session:
                await memory.generate_session_title(session_id, data.message)

            # 11. Maybe trigger summary (async, non-blocking)
            all_messages = history + [HumanMessage(content=human_content)]
            await memory.maybe_summarize(session_id, all_messages)

            # Finish stream
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

        except asyncio.CancelledError:
            # Client disconnected / Aborted
            print(f"Chat stream cancelled for session {session_id}")
            yield f"data: {json.dumps({'type': 'error', 'content': '\\n\\n*[Đã ngắt kết nối]*'})}\n\n"
            if response_text:
                memory.save_message(session_id, "assistant", response_text + "\n\n*[Đã ngắt kết nối]*")
        except Exception as e:
            print(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'\\n\\n*[Lỗi hệ thống: {str(e)}]*'})}\n\n"
            if response_text:
                memory.save_message(session_id, "assistant", response_text + f"\n\n*[Lỗi]*")

    return StreamingResponse(generate_chat_stream(), media_type="text/event-stream")


@router.get("/sessions")
async def list_sessions(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """List all chat sessions for the current user."""
    result = (
        db.table("conversation_sessions")
        .select("id, title, summary, message_count, created_at, updated_at")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return {"data": result.data}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Load all messages for a specific chat session."""
    # Verify session belongs to user
    session = (
        db.table("conversation_sessions")
        .select("id")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not session.data:
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    # Load messages ordered by creation time
    messages = (
        db.table("chat_messages")
        .select("id, role, content, tool_calls, created_at")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )
    return {"data": messages.data}

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Delete a chat session and all its messages (via ON DELETE CASCADE)."""
    # Verify session belongs to user
    session = (
        db.table("conversation_sessions")
        .select("id")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not session.data:
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    # Delete the session. Messages are deleted automatically due to foreign key cascade.
    db.table("conversation_sessions").delete().eq("id", session_id).execute()
    return {"message": "Cuộc trò chuyện đã được xóa"}


_weather_cache = {}

@router.get("/weather")
async def get_weather_data(
    lat: float | None = None,
    lon: float | None = None,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Get current weather data for the user's location (from coords or profile)."""
    memory = MemoryManager(db, user_id)
    default_loc, cache_ttl = memory.get_weather_prefs()
    
    settings = get_settings()
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing OPENWEATHER_API_KEY")

    # Determine query and cache key
    cache_key = ""
    prompt = ""
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        if lat is not None and lon is not None:
            # Reverse geocoding
            geo_url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={api_key}"
            geo_req = urllib.request.Request(geo_url)
            with urllib.request.urlopen(geo_req, context=ctx, timeout=10) as geo_res:
                geo_data = json.loads(geo_res.read())
                if geo_data and len(geo_data) > 0:
                    city_name = geo_data[0].get("local_names", {}).get("vi", geo_data[0].get("name", ""))
                    state = geo_data[0].get("state", "")
                    loc_str = f"{city_name}, {state}" if state else city_name
                    # Round coords to 2 decimals to improve cache hit rate
                    cache_key = f"{round(lat, 2)},{round(lon, 2)}"
                    prompt = f"Thời tiết hiện tại ở {loc_str} thế nào?"
                else:
                    cache_key = f"{round(lat, 2)},{round(lon, 2)}"
                    prompt = f"Thời tiết hiện tại ở tọa độ {lat}, {lon} thế nào?"
        else:
            loc = default_loc or "Trà Vinh"
            cache_key = loc
            prompt = f"Thời tiết hiện tại ở {loc} thế nào?"

        # Check cache
        now = time.time()
        cached_entry = _weather_cache.get(cache_key)
        if cached_entry and now < cached_entry["expire_at"]:
            return cached_entry["data"]

        # Request OpenWeather Assistant
        url = "https://api.openweathermap.org/assistant/session"
        headers = {"Content-Type": "application/json", "X-Api-Key": api_key}
        data = json.dumps({"prompt": prompt}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            res_data = response.read()
            json_res = json.loads(res_data)
            
            if "answer" in json_res or json_res:
                # Add the actual location string to the response so frontend can show it
                if lat is not None and lon is not None and "loc_str" in locals() and loc_str:
                    json_res["location"] = loc_str
                
                # Successfully retrieved data
                _weather_cache[cache_key] = {"data": json_res, "expire_at": now + cache_ttl}
                return json_res
            elif cached_entry:
                # AI didn't return proper data structure, fallback to stale cache
                return cached_entry["data"]
                
            return json_res
            
    except Exception as e:
        if 'cached_entry' in locals() and cached_entry:
            return cached_entry["data"]
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy thông tin thời tiết: {str(e)}")

