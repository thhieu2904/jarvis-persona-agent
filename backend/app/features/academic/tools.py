"""
Academic tools for the agent — uses AcademicService for per-user credentials.
These are LangChain @tool functions that the LangGraph agent can call.

Flow: Tool call → AcademicService → Check cache → If stale, decrypt user
credentials → Login to school API → Fetch → Cache → Return formatted data.
"""

import json
from typing import Annotated
from langchain_core.tools import tool, InjectedToolArg

from app.core.dependencies import get_db
from app.features.academic.service import AcademicService


@tool
async def get_semesters(
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Lấy danh sách tất cả các học kỳ của sinh viên.
    Dùng khi cần biết danh sách học kỳ, học kỳ hiện tại, hoặc mã học kỳ để tra cứu.

    Returns:
        Danh sách học kỳ bao gồm: mã HK, tên HK, ngày bắt đầu/kết thúc.
    """
    try:
        service = AcademicService(get_db())
        client = await service._get_authenticated_client(user_id)

        try:
            data = await client.get_semesters()
        finally:
            await client.close()

        # Format for LLM consumption
        current = data.get("hoc_ky_theo_ngay_hien_tai", "?")
        semesters = data.get("ds_hoc_ky", [])

        result = f"Hoc ky hien tai: {current}\n"
        result += f"Tong so hoc ky: {len(semesters)}\n\n"
        for s in semesters[:6]:  # Limit to recent 6
            result += f"- {s.get('ten_hoc_ky', '?')} (ma: {s.get('hoc_ky', '?')})\n"

        return result

    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "hint": "Chủ nhân cần kết nối tài khoản trường trước (vào Cài đặt > Tài khoản trường).",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Lỗi khi lấy danh sách học kỳ: {str(e)}",
        }, ensure_ascii=False)


@tool
async def get_timetable(
    semester_id: int | None = None,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Lấy thời khóa biểu (TKB) / lịch học theo tuần.
    Dùng khi sinh viên hỏi về lịch học, thời gian học, phòng học, hoặc giảng viên.

    Args:
        semester_id: Mã học kỳ (vd: 20252). Nếu None thì lấy HK hiện tại.

    Returns:
        Thời khóa biểu theo tuần: thứ, tiết, môn, phòng, giảng viên.
    """
    try:
        service = AcademicService(get_db())
        semester_str = str(semester_id) if semester_id else None
        weeks = await service.get_timetable(user_id, semester_str)

        if not weeks:
            return "Không có thời khóa biểu cho học kỳ này (có thể HK chưa bắt đầu)."

        result = f"Tổng số tuần: {len(weeks)}\n\n"
        for w in weeks[:3]:  # Show first 3 weeks
            result += f"Tuần {w.week_number} ({w.start_date} - {w.end_date}):\n"
            for s in w.slots:
                end_period = s.start_period + s.num_periods - 1
                cancelled = " [NGHỈ]" if s.is_cancelled else ""
                result += (
                    f"  Thứ {s.day_of_week} | Tiết {s.start_period}-{end_period} | "
                    f"{s.subject_name} | Phòng {s.room} | "
                    f"GV: {s.lecturer}{cancelled}\n"
                )
            result += "\n"

        return result

    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "hint": "Chủ nhân cần kết nối tài khoản trường trước.",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Lỗi khi lấy TKB: {str(e)}",
        }, ensure_ascii=False)


@tool
async def get_grades(
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Lấy bảng điểm tất cả các học kỳ.
    Dùng khi sinh viên hỏi về điểm số, GPA, kết quả học tập, hoặc xếp loại.

    Returns:
        Bảng điểm theo HK: GPA, điểm từng môn, xếp loại, tín chỉ.
    """
    try:
        service = AcademicService(get_db())
        semesters = await service.get_grades(user_id)

        if not semesters:
            return "Không có dữ liệu điểm."

        result = f"Tổng số học kỳ có điểm: {len(semesters)}\n\n"

        for sem in semesters[:3]:  # Show latest 3 semesters
            result += f"--- {sem.semester_name} ---\n"
            result += f"GPA HK: {sem.gpa_10} (hệ 10) / {sem.gpa_4} (hệ 4)\n"
            result += f"GPA Tích luỹ: {sem.cumulative_gpa_10} (hệ 10) / {sem.cumulative_gpa_4} (hệ 4)\n"
            result += f"Tín chỉ đạt HK: {sem.credits_earned}\n"
            result += f"Xếp loại: {sem.classification}\n"

            for c in sem.courses:
                result += (
                    f"  {c.subject_name} ({c.credits} TC): "
                    f"{c.grade_10} - {c.grade_letter}\n"
                )
            result += "\n"

        return result

    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "hint": "Chủ nhân cần kết nối tài khoản trường trước.",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Lỗi khi lấy điểm: {str(e)}",
        }, ensure_ascii=False)


# Export all tools for the agent graph
academic_tools = [get_semesters, get_timetable, get_grades]
