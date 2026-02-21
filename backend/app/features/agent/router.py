"""
Agent feature: Chat API route.
"""

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from langchain_core.messages import HumanMessage

from app.core.dependencies import get_db, get_current_user_id
from app.features.agent.graph import get_agent_graph
from app.features.agent.memory import MemoryManager

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Chat with the AI agent."""
    memory = MemoryManager(db, user_id)

    # 1. Get or create session
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
        graph = get_agent_graph()
        result = await graph.ainvoke(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # 8. Extract response
    ai_message = result["messages"][-1]
    response_text = ai_message.content

    # 9. Save AI response to DB
    tool_calls = None
    if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
        tool_calls = [
            {"name": tc["name"], "args": tc["args"]}
            for tc in ai_message.tool_calls
        ]
    memory.save_message(session_id, "assistant", response_text, tool_calls)

    # 10. Maybe trigger summary (async, non-blocking)
    all_messages = history + [HumanMessage(content=data.message)]
    await memory.maybe_summarize(session_id, all_messages)

    return ChatResponse(response=response_text, session_id=session_id)


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
