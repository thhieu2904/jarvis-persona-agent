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
            "id": n["id"],
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


@tool
def list_notes(
    pinned_only: bool = False,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Xem danh sách tất cả ghi chú của chủ nhân.
    Dùng khi chủ nhân muốn xem lại tất cả notes, hoặc chỉ notes đã ghim.

    Args:
        pinned_only: True = chỉ xem notes đã ghim. False = xem tất cả.

    Returns:
        Danh sách ghi chú.
    """
    from app.features.notes.service import NotesService

    db = get_db()
    service = NotesService(db)
    notes = service.list_notes(user_id=user_id, pinned_only=pinned_only)

    if not notes:
        return json.dumps({
            "status": "success",
            "message": "Chưa có ghi chú nào.",
            "notes": [],
        }, ensure_ascii=False)

    result_notes = []
    for n in notes[:10]:
        result_notes.append({
            "id": n["id"],
            "content": n["content"][:100] + ("..." if len(n["content"]) > 100 else ""),
            "type": n["note_type"],
            "tags": n.get("tags", []),
            "is_pinned": n.get("is_pinned", False),
            "created_at": n["created_at"],
        })

    return json.dumps({
        "status": "success",
        "message": f"Có {len(notes)} ghi chú.",
        "notes": result_notes,
    }, ensure_ascii=False)


@tool
def update_note(
    note_id: str,
    content: str | None = None,
    tags: list[str] | None = None,
    is_pinned: bool | None = None,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Cập nhật nội dung hoặc tags của ghi chú.
    Dùng khi chủ nhân muốn sửa note, thêm/bớt tags, hoặc ghim/bỏ ghim.
    Trước khi gọi, dùng search_notes() hoặc list_notes() để lấy note_id.

    Args:
        note_id: ID của ghi chú cần cập nhật (lấy từ search/list)
        content: Nội dung mới (None = giữ nguyên)
        tags: Tags mới (None = giữ nguyên)
        is_pinned: True = ghim, False = bỏ ghim (None = giữ nguyên)

    Returns:
        Xác nhận đã cập nhật ghi chú.
    """
    from app.features.notes.service import NotesService

    db = get_db()
    service = NotesService(db)

    update_data = {}
    if content is not None:
        update_data["content"] = content
    if tags is not None:
        update_data["tags"] = tags
    if is_pinned is not None:
        update_data["is_pinned"] = is_pinned

    if not update_data:
        return json.dumps({
            "status": "error",
            "message": "Không có thông tin nào để cập nhật.",
        }, ensure_ascii=False)

    result = service.update_note(user_id=user_id, note_id=note_id, update_data=update_data)

    if not result:
        return json.dumps({
            "status": "error",
            "message": f"Không tìm thấy ghi chú với ID '{note_id}'.",
        }, ensure_ascii=False)

    return json.dumps({
        "status": "success",
        "message": f"Đã cập nhật ghi chú.",
        "updated_fields": list(update_data.keys()),
    }, ensure_ascii=False)


@tool
def delete_note(
    note_id: str,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Lưu trữ (archive) ghi chú — không xóa vĩnh viễn.
    Dùng khi chủ nhân muốn xóa/ẩn một ghi chú cũ.
    Trước khi gọi, dùng search_notes() hoặc list_notes() để lấy note_id.

    Args:
        note_id: ID của ghi chú cần xóa

    Returns:
        Xác nhận ghi chú đã được lưu trữ.
    """
    from app.features.notes.service import NotesService

    db = get_db()
    service = NotesService(db)
    service.delete_note(user_id=user_id, note_id=note_id)

    return json.dumps({
        "status": "success",
        "message": "Đã lưu trữ ghi chú.",
    }, ensure_ascii=False)


# Export all tools for the agent graph
notes_tools = [save_quick_note, search_notes, list_notes, update_note, delete_note]
