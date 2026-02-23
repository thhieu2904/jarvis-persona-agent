"""
Agent feature: LangGraph state machine with ReAct loop.

Architecture:
  User Message → Agent (LLM) → Tool Decision → Execute Tool → Agent → Response
  
Constraints:
  - recursion_limit from AGENT_RECURSION_LIMIT config (default 25)
  - Sliding window memory (last N message pairs)
  - Summary memory for long conversations
"""

from typing import Annotated, TypedDict
import asyncio
import logging

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages

from app.config import get_settings
from app.core.llm_provider import create_llm
from app.features.agent.prompts import build_system_prompt

logger = logging.getLogger(__name__)

# Import tools
from app.features.academic.tools import get_timetable, get_grades, get_semesters
from app.features.tasks.tools import create_task, list_tasks, update_task, complete_task, delete_task
from app.features.notes.tools import save_quick_note, search_notes, list_notes, update_note, delete_note
from app.features.calendar.tools import create_event, get_events, update_event, delete_event
from app.features.agent.tools.web_search import web_tools
from app.features.agent.tools.image_gen import image_tools
from app.features.agent.tools.weather import weather_tools


# ── State Definition ─────────────────────────────────────
class AgentState(TypedDict):
    """State passed through the LangGraph graph."""
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    user_name: str
    user_preferences: str
    user_location: str | None
    default_location: str | None
    conversation_summary: str


# ── All available tools ──────────────────────────────────
ALL_TOOLS = [
    # Academic (Phase 1)
    get_timetable, get_grades, get_semesters,
    # Tasks & Reminders
    create_task, list_tasks, update_task, complete_task, delete_task,
    # Quick Notes
    save_quick_note, search_notes, list_notes, update_note, delete_note,
    # Calendar Events
    create_event, get_events, update_event, delete_event,
    # Web Search & Image Gen (Phase 1)
    *web_tools,
    *image_tools,
    # Weather Tool
    *weather_tools,
]


def build_agent_graph():
    """Build the LangGraph ReAct agent graph.
    
    Returns:
        Compiled graph ready to invoke.
    """
    settings = get_settings()
    
    # LLM with tools bound
    llm = create_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    # ── Node: Agent (LLM decision) ──────────────────────
    def agent_node(state: AgentState) -> dict:
        """LLM processes messages and decides: respond or call tool."""
        # Build system prompt with user context + Vietnam time
        system_msg = SystemMessage(content=build_system_prompt(
            user_name=state.get("user_name", "bạn"),
            user_preferences=state.get("user_preferences", "Chưa có thông tin"),
            user_location=state.get("user_location"),
            default_location=state.get("default_location"),
        ))

        # Prepend summary if exists
        messages = [system_msg]
        if state.get("conversation_summary"):
            messages.append(SystemMessage(
                content=f"Tóm tắt hội thoại trước: {state['conversation_summary']}"
            ))
        messages.extend(state["messages"])

        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # ── Routing: should we call tools or end? ────────────
    def should_continue(state: AgentState) -> str:
        """Route based on whether LLM wants to call tools."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # ── Build Graph ──────────────────────────────────────
    graph = StateGraph(AgentState)

    # Custom tool node: injects user_id from state into InjectedToolArg
    tool_map = {t.name: t for t in ALL_TOOLS}

    # Detect which tools need user_id (those using InjectedToolArg)
    import inspect
    tools_needing_user_id = set()
    for t in ALL_TOOLS:
        try:
            fn = t.func or t.coroutine or getattr(t, '__wrapped__', None)
            if fn is not None:
                sig = inspect.signature(fn)
                if "user_id" in sig.parameters:
                    tools_needing_user_id.add(t.name)
        except (ValueError, TypeError):
            pass  # Skip tools where signature can't be inspected

    async def tool_node(state: AgentState) -> dict:
        """Execute tools with user_id injected from state."""
        from langchain_core.messages import ToolMessage

        last_message = state["messages"][-1]
        user_id = state.get("user_id", "")
        results = []

        for tc in last_message.tool_calls:
            tool_fn = tool_map.get(tc["name"])
            if tool_fn is None:
                results.append(ToolMessage(
                    content=f"Tool '{tc['name']}' không tồn tại. Hãy dùng tool khác.",
                    tool_call_id=tc["id"],
                    name=tc["name"],
                ))
                continue
            args = dict(tc["args"])
            # Only inject user_id for tools that need it
            if tc["name"] in tools_needing_user_id:
                args["user_id"] = user_id

            try:
                logger.info(f"Calling tool: {tc['name']} with args: {tc['args']}")
                if asyncio.iscoroutinefunction(tool_fn.func):
                    result = await tool_fn.ainvoke(args)
                else:
                    result = await tool_fn.ainvoke(args)
                logger.info(f"Tool {tc['name']} returned ({len(str(result))} chars)")
            except Exception as e:
                logger.error(f"Tool {tc['name']} error: {e}")
                result = f"Tool error: {str(e)}"

            results.append(ToolMessage(
                content=str(result),
                tool_call_id=tc["id"],
                name=tc["name"],
            ))

        return {"messages": results}

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")  # After tool → back to agent

    # Compile graph (recursion_limit is now set at invoke time in langgraph 1.x)
    return graph.compile()


# Singleton graph instance
agent_graph = None


def get_agent_graph():
    """Get or create the agent graph (lazy singleton)."""
    global agent_graph
    if agent_graph is None:
        agent_graph = build_agent_graph()
    return agent_graph
