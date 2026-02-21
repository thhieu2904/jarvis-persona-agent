"""
Agent feature: Memory management (short-term, long-term, summary).

3-tier memory system:
  1. Short-term: Sliding window of last N message pairs
  2. Summary: LLM-compressed summary of older messages (saves tokens)
  3. Long-term: User preferences injected into system prompt
"""

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.config import get_settings
from app.core.llm_provider import create_llm
from app.features.agent.prompts import SUMMARY_PROMPT


class MemoryManager:
    """Manages the 3-tier memory system for agent conversations."""

    def __init__(self, db_client, user_id: str):
        self.db = db_client
        self.user_id = user_id
        self.settings = get_settings()

    # ── Short-term: Sliding Window ───────────────────────

    def apply_sliding_window(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """Keep only the last N message pairs in context.
        
        Args:
            messages: Full message history.
            
        Returns:
            Trimmed messages within the window size.
        """
        window = self.settings.AGENT_MEMORY_WINDOW_SIZE * 2  # pairs → individual messages
        if len(messages) <= window:
            return messages
        return messages[-window:]

    # ── Summary Memory ───────────────────────────────────

    async def maybe_summarize(
        self, session_id: str, messages: list[BaseMessage]
    ) -> str | None:
        """If messages exceed threshold, summarize older ones.
        
        Cost: 1 LLM call (~500 input + ~100 output tokens)
        Trigger: When message count > AGENT_SUMMARY_THRESHOLD
        
        Returns:
            Summary string, or None if not triggered.
        """
        threshold = self.settings.AGENT_SUMMARY_THRESHOLD
        if len(messages) <= threshold:
            return None

        # Messages to summarize: everything outside the sliding window
        window = self.settings.AGENT_MEMORY_WINDOW_SIZE * 2
        old_messages = messages[:-window]

        if not old_messages:
            return None

        # Format messages for summary prompt
        formatted = "\n".join(
            f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content}"
            for m in old_messages
            if isinstance(m, (HumanMessage, AIMessage))
        )

        # Call LLM to summarize
        llm = create_llm()
        summary_response = await llm.ainvoke(
            SUMMARY_PROMPT.format(messages=formatted)
        )
        summary = summary_response.content

        # Save summary to DB
        self.db.table("conversation_sessions").update(
            {
                "summary": summary,
                "summary_updated_at": "now()",
            }
        ).eq("id", session_id).execute()

        return summary

    # ── Long-term: User Preferences ──────────────────────

    def get_user_preferences(self) -> str:
        """Load user preferences for system prompt injection.
        
        Returns:
            Formatted string of user preferences.
        """
        result = (
            self.db.table("users")
            .select("preferences, full_name")
            .eq("id", self.user_id)
            .single()
            .execute()
        )

        if not result.data:
            return "Chưa có thông tin"

        prefs = result.data.get("preferences", {})
        if not prefs:
            return "Chưa có thông tin"

        # Format preferences into readable string
        parts = []
        for key, value in prefs.items():
            parts.append(f"- {key}: {value}")
        return "\n".join(parts) if parts else "Chưa có thông tin"

    def get_user_name(self) -> str:
        """Get user's display name."""
        result = (
            self.db.table("users")
            .select("full_name")
            .eq("id", self.user_id)
            .single()
            .execute()
        )
        return result.data.get("full_name", "bạn") if result.data else "bạn"

    # ── Conversation Session Management ──────────────────

    def get_or_create_session(self, session_id: str | None = None) -> dict:
        """Get existing session or create a new one.
        
        Returns:
            Session record dict with id, summary, message_count.
        """
        if session_id:
            result = (
                self.db.table("conversation_sessions")
                .select("*")
                .eq("id", session_id)
                .eq("user_id", self.user_id)
                .single()
                .execute()
            )
            if result.data:
                return result.data

        # Create new session
        result = (
            self.db.table("conversation_sessions")
            .insert({"user_id": self.user_id, "is_active": True})
            .execute()
        )
        return result.data[0]

    def save_message(self, session_id: str, role: str, content: str, tool_calls: dict | None = None):
        """Save a chat message to the database."""
        self.db.table("chat_messages").insert({
            "session_id": session_id,
            "role": role,
            "content": content,
            "tool_calls": tool_calls,
        }).execute()

        # Increment message count
        self.db.rpc("increment_message_count", {"session_id_param": session_id}).execute()

    def load_session_messages(self, session_id: str) -> list[BaseMessage]:
        """Load chat history for a session from DB."""
        result = (
            self.db.table("chat_messages")
            .select("role, content")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )

        messages = []
        for msg in result.data:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        return messages
