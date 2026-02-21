"""
Notes feature: Agent tools for quick note management.
These are LangChain @tool functions that the LangGraph agent can call.
"""

import json
from typing import Annotated
from langchain_core.tools import tool, InjectedToolArg

from app.core.dependencies import get_db


@tool
def save_quick_note(
    content: str,
    tags: list[str] = None,
    note_type: str = "note",
    url: str = None,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Lưu ghi chú nhanh cho chủ nhân.
    Tự động trích xuất 2-3 từ khóa quan trọng nhất từ nội dung
    để làm tags nếu user không chỉ định rõ.

    Sử dụng khi chủ nhân muốn:
    - Lưu ý tưởng, ghi chú nhanh
    - Bookmark một link
    - Note lại thông tin quan trọng

    Args:
        content: Nội dung ghi chú
        tags: Danh sách tags phân loại (tự trích xuất từ nội dung nếu không có)
        note_type: Loại ghi chú: "note" (mặc định), "idea", "link", "snippet"
        url: URL nếu chủ nhân muốn bookmark link
    
    Returns:
        Xác nhận ghi chú đã được lưu.
    """
    from app.features.notes.service import NotesService

    db = get_db()
    service = NotesService(db)

    note = service.create_note(
        user_id=user_id,
        content=content,
        note_type=note_type,
        tags=tags,
        url=url,
    )

    return json.dumps({
        "status": "success",
        "message": f"Đã lưu ghi chú: '{content[:50]}...' " if len(content) > 50 else f"Đã lưu ghi chú: '{content}'",
        "note_id": note["id"],
        "tags": note.get("tags", []),
    }, ensure_ascii=False)


@tool
def search_notes(
    query: str,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Tìm kiếm trong ghi chú đã lưu của chủ nhân.
    Dùng khi chủ nhân hỏi về thông tin đã note/lưu lại trước đây.

    Args:
        query: Từ khóa tìm kiếm

    Returns:
        Danh sách ghi chú phù hợp.
    """
    from app.features.notes.service import NotesService

    db = get_db()
    service = NotesService(db)

    notes = service.search_notes(
        user_id=user_id,
        query=query,
    )

    if not notes:
        return json.dumps({
            "status": "success",
            "message": f"Không tìm thấy ghi chú nào liên quan đến '{query}'.",
            "notes": [],
        }, ensure_ascii=False)

    result_notes = []
    for n in notes[:5]:
        result_notes.append({
            "content": n["content"],
            "type": n["note_type"],
            "tags": n.get("tags", []),
            "url": n.get("url"),
            "created_at": n["created_at"],
        })

    return json.dumps({
        "status": "success",
        "message": f"Tìm thấy {len(notes)} ghi chú liên quan.",
        "notes": result_notes,
    }, ensure_ascii=False)


# Export all tools for the agent graph
notes_tools = [save_quick_note, search_notes]
