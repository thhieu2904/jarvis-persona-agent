"""
Agent feature: Chat API route.
"""

import uuid
import os
import json
import asyncio

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

    # 6. Prepare state
    state = {
        "messages": trimmed_history,
        "user_id": user_id,
        "user_name": memory.get_user_name(),
        "user_preferences": memory.get_user_preferences(),
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

