"""
Agent feature: Chat API route.
"""

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from langchain_core.messages import HumanMessage, ToolMessage

from app.core.dependencies import get_db, get_current_user_id
from app.features.agent.graph import get_agent_graph
from app.features.agent.memory import MemoryManager

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ToolResult(BaseModel):
    tool_name: str
    tool_args: dict = {}
    result: str


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_results: list[ToolResult] = []
    tools_used: list[str] = []


@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Chat with the AI agent."""
    memory = MemoryManager(db, user_id)

    # 1. Get or create session
    is_new_session = data.session_id is None
    session = memory.get_or_create_session(data.session_id)
    session_id = session["id"]

    # 2. Load conversation history
    history = memory.load_session_messages(session_id)

    # 3. Apply sliding window
    trimmed_history = memory.apply_sliding_window(history)

    # 4. Add new user message
    trimmed_history.append(HumanMessage(content=data.message))

    # 5. Save user message to DB
    memory.save_message(session_id, "user", data.message)

    # 6. Prepare state
    state = {
        "messages": trimmed_history,
        "user_id": user_id,
        "user_name": memory.get_user_name(),
        "user_preferences": memory.get_user_preferences(),
        "conversation_summary": session.get("summary", ""),
    }

    # 7. Run agent graph
    try:
        from app.config import get_settings
        graph = get_agent_graph()
        result = await graph.ainvoke(
            state,
            config={"recursion_limit": get_settings().AGENT_RECURSION_LIMIT},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # 8. Extract response and tool results
    ai_message = result["messages"][-1]
    response_content = ai_message.content

    # Gemini 3 may return content as list of {'type':'text','text':'...'} dicts
    if isinstance(response_content, list):
        response_text = "\n".join(
            part["text"] for part in response_content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    else:
        response_text = str(response_content)

    # Extract tool results from message history for transparency
    tool_results = []
    tool_calls_data = []
    for msg in result["messages"]:
        # Collect tool call args
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_data.append({"name": tc["name"], "args": tc.get("args", {})})
        # Collect tool results
        if isinstance(msg, ToolMessage):
            # Find matching tool call args
            matching_args = {}
            for tc_data in tool_calls_data:
                if tc_data["name"] == msg.name:
                    matching_args = tc_data["args"]
                    break
            # Clean args: remove user_id for privacy
            clean_args = {k: v for k, v in matching_args.items() if k != "user_id"}
            tool_results.append(ToolResult(
                tool_name=msg.name,
                tool_args=clean_args,
                result=str(msg.content)[:2000],  # Limit size
            ))

    # 9. Save AI response to DB (include tool_calls for DB record)
    saved_tool_calls = None
    if tool_calls_data:
        saved_tool_calls = [{"name": tc["name"], "args": tc["args"]} for tc in tool_calls_data]
    memory.save_message(session_id, "assistant", response_text, saved_tool_calls)

    # 10. Maybe trigger summary (async, non-blocking)
    all_messages = history + [HumanMessage(content=data.message)]
    await memory.maybe_summarize(session_id, all_messages)

    # 11. Auto-generate session title for new sessions
    if is_new_session:
        await memory.generate_session_title(session_id, data.message)

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        tool_results=tool_results,
        tools_used=list(set(tc["name"] for tc in tool_calls_data)) if tool_calls_data else [],
    )


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

