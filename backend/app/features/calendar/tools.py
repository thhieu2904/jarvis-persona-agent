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


# Export all tools for the agent graph
calendar_tools = [create_event, get_events]
