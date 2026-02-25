"""
Knowledge feature: Agent tools for RAG-based knowledge retrieval.
These are LangChain @tool functions that the LangGraph agent can call.
"""

import json
from typing import Annotated
from langchain_core.tools import tool, InjectedToolArg

from app.core.dependencies import get_db
from app.features.knowledge.service import KnowledgeService


@tool
def search_memories(
    query: str,
    tags: list[str] | None = None,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Tìm kiếm trong ký ức/ghi chú của chủ nhân bằng ngữ nghĩa (semantic search).
    Dùng khi chủ nhân hỏi về thông tin đã từng lưu trữ, ví dụ:
    - "Hôm trước tao bảo lưu cái gì ấy nhỉ?"
    - "Mật khẩu wifi gì ấy?"
    - "Ghi chú về buổi họp tuần trước?"

    Args:
        query: Câu hỏi hoặc từ khóa tìm kiếm (tiếng Việt hoặc tiếng Anh).
        tags: Lọc theo tags cụ thể (tùy chọn). Ví dụ: ["wifi", "mật khẩu"]

    Returns:
        Danh sách ghi chú liên quan nhất, sắp xếp theo độ tương đồng.
    """
    db = get_db()
    service = KnowledgeService(db)

    results = service.search_notes_by_vector(
        user_id=user_id,
        query=query,
        top_k=5,
        tags=tags,
    )

    if not results:
        return json.dumps({
            "status": "success",
            "message": "Không tìm thấy ghi chú nào liên quan.",
            "memories": [],
        }, ensure_ascii=False)

    memories = []
    for r in results:
        memories.append({
            "id": r.get("id"),
            "content": r.get("content"),
            "note_type": r.get("note_type"),
            "tags": r.get("tags", []),
            "created_at": r.get("created_at"),
            "similarity": round(r.get("similarity", 0), 4),
        })

    return json.dumps({
        "status": "success",
        "message": f"Tìm thấy {len(memories)} ghi chú liên quan.",
        "memories": memories,
    }, ensure_ascii=False)


@tool
def save_memory(
    content: str,
    tags: list[str] | None = None,
    note_type: str = "memory",
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Lưu thông tin quan trọng vào bộ nhớ dài hạn của chủ nhân.
    Dùng khi chủ nhân yêu cầu ghi nhớ điều gì đó, ví dụ:
    - "Nhớ hộ tao mật khẩu wifi là abc123"
    - "Lưu cái này vào não đi"
    - "Ghi nhớ: ngày mai họp lúc 3h"

    Agent NÊN tự động tóm tắt nội dung cuộc trò chuyện trước khi lưu.

    Args:
        content: Nội dung cần ghi nhớ (nên viết rõ ràng, đầy đủ ngữ cảnh).
        tags: Danh sách tag để phân loại. Ví dụ: ["wifi", "mật khẩu"]
        note_type: Loại ghi chú: "memory" (mặc định), "note", "idea", "snippet"

    Returns:
        Xác nhận đã lưu vào bộ nhớ.
    """
    from app.features.notes.service import NotesService

    db = get_db()
    service = NotesService(db)

    note = service.create_note(
        user_id=user_id,
        content=content,
        note_type=note_type,
        tags=tags or [],
    )

    # Trigger embedding calculation (synchronous inside tool since agent runs in background)
    from app.background.embedding_tasks import process_note_embedding
    process_note_embedding(note["id"], content)

    return json.dumps({
        "status": "success",
        "message": f"Đã lưu vào bộ nhớ: '{content[:50]}...'",
        "note_id": note["id"],
        "tags": tags or [],
    }, ensure_ascii=False)


# Export all knowledge tools for the agent graph
knowledge_tools = [search_memories, save_memory]
