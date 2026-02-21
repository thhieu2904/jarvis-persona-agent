"""
Agent feature: LangGraph state machine with ReAct loop.

Architecture:
  User Message → Agent (LLM) → Tool Decision → Execute Tool → Agent → Response
  
Constraints:
  - recursion_limit=5 (max 5 steps per turn)
  - Sliding window memory (last N message pairs)
  - Summary memory for long conversations
"""

from typing import Annotated, TypedDict
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.config import get_settings
from app.core.llm_provider import create_llm
from app.features.agent.prompts import SYSTEM_PROMPT

# Import tools
from app.features.academic.tools import get_timetable, get_grades, get_semesters
from app.features.tasks.tools import create_task, list_tasks


# ── State Definition ─────────────────────────────────────
class AgentState(TypedDict):
    """State passed through the LangGraph graph."""
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    user_name: str
    user_preferences: str
    conversation_summary: str


# ── All available tools ──────────────────────────────────
ALL_TOOLS = [get_timetable, get_grades, get_semesters, create_task, list_tasks]


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
        # Build system prompt with user context
        system_msg = SystemMessage(content=SYSTEM_PROMPT.format(
            user_name=state.get("user_name", "bạn"),
            user_preferences=state.get("user_preferences", "Chưa có thông tin"),
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)"),
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

    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")  # After tool → back to agent

    # Compile with recursion limit
    return graph.compile(
        # checkpointer can be added for persistence
        recursion_limit=settings.AGENT_RECURSION_LIMIT,
    )


# Singleton graph instance
agent_graph = None


def get_agent_graph():
    """Get or create the agent graph (lazy singleton)."""
    global agent_graph
    if agent_graph is None:
        agent_graph = build_agent_graph()
    return agent_graph
