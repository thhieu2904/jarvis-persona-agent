"""
Calendar feature: Agent tools for event management.
These are LangChain @tool functions that the LangGraph agent can call.
"""

import json
from typing import Annotated
from datetime import datetime
from langchain_core.tools import tool, InjectedToolArg

from app.core.dependencies import get_db


@tool
def create_event(
    title: str,
    start_time: str,
    end_time: str = None,
    event_type: str = "personal",
    location: str = None,
    description: str = None,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Tạo sự kiện/lịch hẹn mới cho chủ nhân.
    Dùng cho MỌI sự kiện NGOÀI thời khóa biểu trường:
    lịch họp CLB, sinh nhật, hẹn café, deadline cá nhân, lịch học thêm...

    Nếu chủ nhân mô tả lịch lặp phức tạp (ví dụ: "mỗi thứ 3 hàng tuần"),
    hãy tạo nhiều event đơn lẻ (4-8 events) thay vì dùng recurrence.

    Args:
        title: Tên sự kiện (cái gì)
        start_time: Thời gian bắt đầu, ISO format: YYYY-MM-DDTHH:MM
        end_time: Thời gian kết thúc (tùy chọn), ISO format: YYYY-MM-DDTHH:MM
        event_type: Loại: "personal", "club", "study_group", "birthday", "other"
        location: Địa điểm (tùy chọn)
        description: Mô tả chi tiết (tùy chọn)

    Returns:
        Xác nhận sự kiện đã được tạo.
    """
    from app.features.calendar.service import CalendarService

    db = get_db()
    service = CalendarService(db)

    event = service.create_event(
        user_id=user_id,
        title=title,
        start_time=start_time,
        end_time=end_time,
        description=description,
        event_type=event_type,
        location=location,
        source="agent",
    )

    return json.dumps({
        "status": "success",
        "message": f"Đã tạo sự kiện: '{title}' vào {start_time}",
        "event_id": event["id"],
    }, ensure_ascii=False)


@tool
def get_events(
    date: str = None,
    event_type: str = None,
    days_ahead: int = 7,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Xem sự kiện/lịch hẹn của chủ nhân.
    Dùng khi chủ nhân hỏi về lịch, sự kiện sắp tới, hoặc kế hoạch.
    KHÔNG bao gồm thời khóa biểu trường (dùng get_timetable cho TKB).

    Args:
        date: Ngày bắt đầu xem (YYYY-MM-DD). Mặc định = hôm nay.
        event_type: Lọc theo loại: "personal", "club", "study_group", "birthday", "other". None = tất cả.
        days_ahead: Số ngày muốn xem phía trước. Mặc định = 7 ngày.

    Returns:
        Danh sách sự kiện trong khoảng thời gian.
    """
    from app.features.calendar.service import CalendarService

    db = get_db()
    service = CalendarService(db)

    events = service.get_events(
        user_id=user_id,
        date=date,
        event_type=event_type,
        days_range=days_ahead,
    )

    if not events:
        period = f"từ {date}" if date else "trong tuần tới"
        return json.dumps({
            "status": "success",
            "message": f"Không có sự kiện nào {period}.",
            "events": [],
        }, ensure_ascii=False)

    result_events = []
    for e in events:
        result_events.append({
            "id": e["id"],
            "title": e["title"],
            "start_time": e["start_time"],
            "end_time": e.get("end_time"),
            "type": e["event_type"],
            "location": e.get("location"),
            "description": e.get("description"),
        })

    return json.dumps({
        "status": "success",
        "message": f"Có {len(events)} sự kiện.",
        "events": result_events,
    }, ensure_ascii=False)


@tool
def update_event(
    event_id: str,
    title: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    location: str | None = None,
    description: str | None = None,
    event_type: str | None = None,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Cập nhật sự kiện/lịch hẹn đã tồn tại.
    Dùng khi chủ nhân muốn đổi giờ, địa điểm, hoặc tên sự kiện.
    Trước khi gọi, dùng get_events() để lấy event_id cần sửa.

    Args:
        event_id: ID của sự kiện cần cập nhật (lấy từ get_events)
        title: Tên mới (None = giữ nguyên)
        start_time: Giờ bắt đầu mới, YYYY-MM-DDTHH:MM (None = giữ nguyên)
        end_time: Giờ kết thúc mới (None = giữ nguyên)
        location: Địa điểm mới (None = giữ nguyên)
        description: Mô tả mới (None = giữ nguyên)
        event_type: Loại sự kiện mới (None = giữ nguyên)

    Returns:
        Xác nhận đã cập nhật sự kiện.
    """
    from app.features.calendar.service import CalendarService

    db = get_db()
    service = CalendarService(db)

    update_data = {}
    if title is not None:
        update_data["title"] = title
    if start_time is not None:
        update_data["start_time"] = start_time
    if end_time is not None:
        update_data["end_time"] = end_time
    if location is not None:
        update_data["location"] = location
    if description is not None:
        update_data["description"] = description
    if event_type is not None:
        update_data["event_type"] = event_type

    if not update_data:
        return json.dumps({
            "status": "error",
            "message": "Không có thông tin nào để cập nhật.",
        }, ensure_ascii=False)

    result = service.update_event(user_id=user_id, event_id=event_id, update_data=update_data)

    if not result:
        return json.dumps({
            "status": "error",
            "message": f"Không tìm thấy sự kiện với ID '{event_id}'.",
        }, ensure_ascii=False)

    return json.dumps({
        "status": "success",
        "message": f"Đã cập nhật sự kiện '{result['title']}'.",
        "updated_fields": list(update_data.keys()),
    }, ensure_ascii=False)


@tool
def delete_event(
    event_id: str,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Xóa sự kiện/lịch hẹn.
    Chỉ xóa khi chủ nhân yêu cầu rõ ràng. Hỏi xác nhận trước khi xóa.
    Trước khi gọi, dùng get_events() để xác định đúng event_id.

    Args:
        event_id: ID của sự kiện cần xóa

    Returns:
        Xác nhận sự kiện đã bị xóa.
    """
    from app.features.calendar.service import CalendarService

    db = get_db()
    service = CalendarService(db)

    # Get event info before deleting
    event = service.get_event_by_id(user_id=user_id, event_id=event_id)
    if not event:
        return json.dumps({
            "status": "error",
            "message": f"Không tìm thấy sự kiện với ID '{event_id}'.",
        }, ensure_ascii=False)

    title = event["title"]
    service.delete_event(user_id=user_id, event_id=event_id)

    return json.dumps({
        "status": "success",
        "message": f"Đã xóa sự kiện '{title}'.",
    }, ensure_ascii=False)


# Export all tools for the agent graph
calendar_tools = [create_event, get_events, update_event, delete_event]
