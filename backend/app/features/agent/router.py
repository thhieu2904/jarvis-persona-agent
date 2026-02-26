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
    display_message: str | None = None  # Clean version for DB/UI (strips SYS_FILE blocks)


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

    # 5. Save user message to DB (use display_message if provided to avoid storing raw SYS_FILE dumps)
    db_content = _build_db_content(data.display_message or data.message, data.images)
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
        "platform": "web",
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


class RoutineScheduleRequest(BaseModel):
    routine_type: str  # "morning" or "evening"
    time: str | None = None  # "HH:MM" format or null to disable
    prompt: str | None = None  # Custom routine prompt


@router.put("/routine_schedule")
async def update_routine_schedule(
    data: RoutineScheduleRequest,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Update routine schedule (morning/evening briefing time).

    Set time to null to disable a routine.
    """
    from app.background.scheduler import update_routine_schedule as update_schedule

    if data.routine_type not in ("morning", "evening"):
        raise HTTPException(status_code=400, detail="routine_type phải là 'morning' hoặc 'evening'")

    # Validate time format if provided
    if data.time:
        try:
            h, m = map(int, data.time.split(":"))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Định dạng giờ phải là HH:MM (vd: 06:30)")

    # Update preferences in DB
    pref_key_time = f"{data.routine_type}_routine_time"
    pref_key_prompt = f"{data.routine_type}_routine_prompt"
    result = (
        db.table("users")
        .select("preferences")
        .eq("id", user_id)
        .single()
        .execute()
    )
    prefs = result.data.get("preferences", {}) if result.data else {}
    
    if data.time is not None:
        prefs[pref_key_time] = data.time
    else:
        prefs.pop(pref_key_time, None)
        
    if data.prompt is not None:
        prefs[pref_key_prompt] = data.prompt

    db.table("users").update({"preferences": prefs}).eq("id", user_id).execute()

    # Sync APScheduler in-memory job
    job_id = f"{data.routine_type}_routine_job"
    update_schedule(job_id, data.time)

    return {
        "message": f"{'Đã đặt' if data.time else 'Đã tắt'} báo cáo {data.routine_type} {'lúc ' + data.time if data.time else ''}",
        "routine_type": data.routine_type,
        "time": data.time,
    }


@router.get("/available_tools")
async def get_available_tools():
    """Get list of available tools to be used in routine custom prompts."""
    return [
        {"id": "weather", "label": "🌤️ Thời tiết", "text": "[Xem thời tiết tại {{location}}]"},
        {"id": "timetable", "label": "📅 Lịch học", "text": "[Đọc lịch học ngày {{current_date}}]"},
        {"id": "tasks", "label": "✅ Công việc", "text": "[Rà soát các task đến hạn/quá hạn]"},
        {"id": "news", "label": "📰 Tin tức", "text": "[Tìm 3 tin tức nổi bật hôm nay]"},
        {"id": "greeting", "label": "💖 Lời chúc", "text": "[Viết một lời chúc tạo động lực]"}
    ]

@router.get("/routine_schedule")
async def get_routine_schedule(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Get current routine schedule settings."""
    result = (
        db.table("users")
        .select("preferences")
        .eq("id", user_id)
        .single()
        .execute()
    )
    prefs = result.data.get("preferences", {}) if result.data else {}
    return {
        "morning_routine_time": prefs.get("morning_routine_time"),
        "evening_routine_time": prefs.get("evening_routine_time"),
        "morning_routine_prompt": prefs.get("morning_routine_prompt"),
        "evening_routine_prompt": prefs.get("evening_routine_prompt"),
    }
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


# ══════════════════════════════════════════════════════════
# ── Zalo Webhook (Inbound) ────────────────────────────────
# ══════════════════════════════════════════════════════════

import logging
from time import time as time_now
from fastapi import BackgroundTasks, Request
import httpx

_webhook_logger = logging.getLogger(__name__)

# Dedup set: {message_id: timestamp} — tránh xử lý lại khi Zalo retry
_processed_message_ids: dict[str, float] = {}
_DEDUP_TTL_SECONDS = 300  # 5 phút


def _cleanup_dedup():
    """Xóa message_id cũ hơn TTL."""
    cutoff = time_now() - _DEDUP_TTL_SECONDS
    expired = [k for k, v in _processed_message_ids.items() if v < cutoff]
    for k in expired:
        del _processed_message_ids[k]


async def _process_zalo_message(user_text: str, chat_id: str,
                                 db_url: str, db_key: str):
    """Background task: gọi LangGraph + gửi reply qua Zalo."""
    from supabase import create_client
    from langchain_core.messages import HumanMessage
    from app.features.agent.graph import get_agent_graph
    from app.features.agent.memory import MemoryManager
    from app.background.scheduler import _get_owner_user_id
    from app.core.zalo import send_zalo_message, send_zalo_photo, send_zalo_sticker
    from app.core.zalo_formatter import ZaloFormatter, get_sticker_id

    try:
        db = create_client(db_url, db_key)
        user_id = _get_owner_user_id()
        if not user_id:
            await send_zalo_message("❌ JARVIS: Không tìm thấy tài khoản.", chat_id)
            return

        memory = MemoryManager(db, user_id)
        channel_key = f"zalo_{chat_id}"
        session = memory.get_or_create_session(channel_key=channel_key)
        session_id = session["id"]

        history = memory.load_session_messages(session_id)
        is_first_message = len(history) == 0  # Session mới → gửi sticker chào
        trimmed_history = memory.apply_sliding_window(history)
        trimmed_history.append(HumanMessage(content=user_text))
        memory.save_message(session_id, "user", user_text)

        default_loc, _ = memory.get_weather_prefs()

        state = {
            "messages": trimmed_history,
            "user_id": user_id,
            "user_name": memory.get_user_name(),
            "user_preferences": memory.get_user_preferences(),
            "user_location": None,
            "default_location": default_loc,
            "conversation_summary": session.get("summary", ""),
            "platform": "zalo",
        }

        settings = get_settings()
        graph = get_agent_graph()
        result = await graph.ainvoke(
            state,
            config={"recursion_limit": settings.AGENT_RECURSION_LIMIT},
        )

        # Extract response text
        ai_message = result["messages"][-1]
        response_content = ai_message.content
        if isinstance(response_content, list):
            response_text = "\n".join(
                part["text"] for part in response_content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        else:
            response_text = str(response_content)

        # Save AI response to DB (hiện trên Web UI)
        memory.save_message(session_id, "assistant", response_text)

        # Format for Zalo: tách ảnh + strip markdown
        image_urls, clean_text = ZaloFormatter.extract_images_and_clean(response_text)

        # Gửi ảnh tuần tự TRƯỚC text (fix race condition)
        for img_url in image_urls:
            await send_zalo_photo(img_url, chat_id=chat_id)
            await asyncio.sleep(0.5)

        # Gửi sticker chào khi bắt đầu session mới (chỉ lần đầu)
        if is_first_message:
            greeting_sticker = get_sticker_id("VAY_TAY")
            if greeting_sticker:
                await send_zalo_sticker(greeting_sticker, chat_id=chat_id)
                await asyncio.sleep(0.3)

        # Gửi text trực tiếp (skip sticker LLM chain để giảm latency ~2s)
        if clean_text:
            await send_zalo_message(clean_text, chat_id=chat_id)

    except Exception as e:
        _webhook_logger.error(f"Zalo webhook background error: {e}", exc_info=True)
        from app.core.zalo import send_zalo_message
        await send_zalo_message(f"⚠️ JARVIS gặp lỗi: {str(e)[:200]}", chat_id)


@router.post("/webhook/zalo")
async def zalo_webhook(request: Request, background_tasks: BackgroundTasks):
    """Zalo Bot Inbound Webhook.

    Trả 200 OK ngay lập tức để tránh Zalo timeout/retry.
    Xử lý LangGraph ở background task.
    """
    settings = get_settings()

    # 1. Validate Zalo secret token
    secret = request.headers.get("X-Bot-Api-Secret-Token", "")
    if not settings.ZALO_WEBHOOK_SECRET or secret != settings.ZALO_WEBHOOK_SECRET:
        _webhook_logger.warning("Zalo webhook: invalid secret token")
        return {"ok": True}

    try:
        data = await request.json()
    except Exception:
        return {"ok": True}

    # Zalo webhook payload: event_name + message at top level
    # (API docs show "result" wrapper but actual payload is flat)
    result = data.get("result", data)  # fallback to data itself if no "result" key
    event_name = result.get("event_name", "")

    # 2. Chỉ xử lý text message (bỏ qua sticker, ảnh, v.v.)
    if event_name != "message.text.received":
        return {"ok": True}

    message_obj = result.get("message", {})
    chat_id = message_obj.get("chat", {}).get("id", "")
    message_id = message_obj.get("message_id", "")
    user_text = message_obj.get("text", "").strip()

    if not chat_id or not user_text:
        return {"ok": True}

    # 3. Chỉ phản hồi owner (bảo mật cục bộ)
    if chat_id != settings.ZALO_CHAT_ID:
        _webhook_logger.info(f"Zalo webhook: rejected non-owner chat_id={chat_id[:8]}...")
        return {"ok": True}

    # 4. Dedup: chống xử lý lại khi Zalo retry
    _cleanup_dedup()
    if message_id and message_id in _processed_message_ids:
        _webhook_logger.info(f"Zalo webhook: skipping duplicate message_id={message_id[:12]}")
        return {"ok": True}
    if message_id:
        _processed_message_ids[message_id] = time_now()

    # 5. Trả 200 OK ngay → xử lý ở background (tránh Zalo timeout 3-5s)
    background_tasks.add_task(
        _process_zalo_message,
        user_text=user_text,
        chat_id=chat_id,
        db_url=settings.SUPABASE_URL,
        db_key=settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
    )

    return {"ok": True}


class ZaloWebhookSetupRequest(BaseModel):
    webhook_url: str  # VD: https://xxxx.ngrok-free.app/api/agent/webhook/zalo


@router.post("/webhook/zalo/setup")
async def setup_zalo_webhook(data: ZaloWebhookSetupRequest):
    """Đăng ký/cập nhật Webhook URL với Zalo Bot API (gọi 1 lần sau khi ngrok up)."""
    settings = get_settings()
    token = settings.ZALO_BOT_TOKEN
    secret = settings.ZALO_WEBHOOK_SECRET

    if not token:
        raise HTTPException(status_code=500, detail="ZALO_BOT_TOKEN chưa được cấu hình")
    if not secret:
        raise HTTPException(status_code=500, detail="ZALO_WEBHOOK_SECRET chưa được cấu hình")

    url = f"https://bot-api.zaloplatforms.com/bot{token}/setWebhook"
    payload = {"url": data.webhook_url, "secret_token": secret}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload)
        return resp.json()
