"""
Academic tools for the agent — uses AcademicService for per-user credentials.
These are LangChain @tool functions that the LangGraph agent can call.

Flow: Tool call → AcademicService → Check cache → If stale, decrypt user
credentials → Login to school API → Fetch → Cache → Return formatted data.
"""

import json
from datetime import datetime, date, timezone, timedelta
from typing import Annotated
from langchain_core.tools import tool, InjectedToolArg

from app.core.dependencies import get_db
from app.features.academic.service import AcademicService
from app.features.academic.schemas import WeekTimetable

# Vietnam timezone (UTC+7) — instant, no HTTP call needed
VN_TZ = timezone(timedelta(hours=7))


def _find_current_week_index(weeks: list[WeekTimetable], target: date) -> int:
    """Return the index of the week containing `target` date.
    
    Falls back to the first week with upcoming slots if target is before
    the semester, or the last week if target is after the semester.
    
    Date format in WeekTimetable is DD/MM/YYYY.
    """
    for i, w in enumerate(weeks):
        try:
            start = datetime.strptime(w.start_date, "%d/%m/%Y").date()
            end = datetime.strptime(w.end_date, "%d/%m/%Y").date()
            if start <= target <= end:
                return i
        except ValueError:
            continue

    # Target is outside semester range — find closest future week with slots
    for i, w in enumerate(weeks):
        try:
            start = datetime.strptime(w.start_date, "%d/%m/%Y").date()
            if start >= target and w.slots:
                return i
        except ValueError:
            continue

    return 0  # Fallback: first week


def _format_weeks(weeks: list[WeekTimetable], start_index: int, max_weeks: int = 3) -> str:
    """Format a window of weeks into a compact string for the LLM.
    
    Skips empty weeks (no slots) but still counts them toward max_weeks
    so we don't scan the entire semester looking for non-empty weeks.
    """
    result = ""
    shown = 0
    i = start_index

    while i < len(weeks) and shown < max_weeks:
        w = weeks[i]
        if not w.slots:
            # Still count this as part of the window, but note it's empty
            result += f"Tuần {w.week_number} ({w.start_date} - {w.end_date}): Không có lịch học\n\n"
        else:
            day_map = {2: "Thứ 2", 3: "Thứ 3", 4: "Thứ 4", 5: "Thứ 5", 6: "Thứ 6", 7: "Thứ 7", 8: "CN"}
            result += f"Tuần {w.week_number} ({w.start_date} - {w.end_date}):\n"
            for s in w.slots:
                end_period = s.start_period + s.num_periods - 1
                cancelled = " [NGHỈ]" if s.is_cancelled else ""
                day_label = day_map.get(s.day_of_week, f"Thứ {s.day_of_week}")
                result += (
                    f"  {day_label} | Tiết {s.start_period}-{end_period} | "
                    f"{s.subject_name} | Phòng {s.room} | "
                    f"GV: {s.lecturer}{cancelled}\n"
                )
            result += "\n"
        shown += 1
        i += 1

    return result.strip()


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
            "message": f"Lỗi khi lấy danh sách học kỳ ({type(e).__name__}): {str(e)}",
        }, ensure_ascii=False)


@tool
async def get_timetable(
    semester_id: int | None = None,
    target_date: str | None = None,
    timetable_type: int = 1,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Lấy thời khóa biểu (TKB) / lịch học theo tuần.
    Dùng khi sinh viên hỏi về lịch học, thời gian học, phòng học, hoặc giảng viên.

    Trả về window 3 tuần: tuần chứa `target_date` (hoặc tuần hiện tại nếu không truyền)
    và 2 tuần tiếp theo. Chỉ truyền semester_id khi muốn xem HK khác với HK hiện tại.

    Args:
        semester_id: Mã học kỳ (vd: 20252). Nếu None thì lấy HK hiện tại.
        target_date: Ngày cần xem lịch, định dạng YYYY-MM-DD (vd: "2026-03-10").
                     Nếu None thì dùng giờ thực của server nhà trường (Vietnam time).
        timetable_type: Loại TKB. 1=cá nhân (mặc định), 2=lớp sinh viên,
                        3=lớp, 4=môn học, 6=khoa quản lý sinh viên.

    Returns:
        Thời khóa biểu 3 tuần: thứ, tiết, môn, phòng, giảng viên.
    """
    try:
        service = AcademicService(get_db())
        semester_str = str(semester_id) if semester_id else None
        weeks = await service.get_timetable(user_id, semester_str, timetable_type)

        if not weeks:
            return "Không có thời khóa biểu cho học kỳ này (có thể HK chưa bắt đầu)."

        # Resolve target date — prefer school server time to avoid UTC vs GMT+7 mismatch
        if target_date:
            try:
                pivot = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                pivot = datetime.now(VN_TZ).date()
        else:
            pivot = datetime.now(VN_TZ).date()

        start_index = _find_current_week_index(weeks, pivot)
        header = f"Ngày tra cứu: {pivot.strftime('%d/%m/%Y')} | Tổng số tuần trong HK: {len(weeks)}\n\n"
        body = _format_weeks(weeks, start_index, max_weeks=3)

        return header + (body if body else "Không có lịch học trong khoảng thời gian này.")

    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "hint": "Chủ nhân cần kết nối tài khoản trường trước.",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Lỗi khi lấy TKB ({type(e).__name__}): {str(e)}",
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
            "message": f"Lỗi khi lấy điểm ({type(e).__name__}): {str(e)}",
        }, ensure_ascii=False)


# Export all tools for the agent graph
academic_tools = [get_semesters, get_timetable, get_grades]
