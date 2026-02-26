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


def _period_to_time(start_period: int, num_periods: int) -> str:
    """Convert TVU period number + count to a human-readable time range.

    TVU schedule rules:
      - Morning session : period  1–5,  starts 07:00
      - Afternoon session: period  6–10, starts 13:00
      - Each period = 45 min
      - Break of 30 min after the 2nd period within each session
          Morning  : after period 2  (08:30 – 09:00)
          Afternoon: after period 7  (14:30 – 15:00)

    Examples:
      (1, 4) → "07:00–10:30"   (tiết 1-4 sáng, 2 tiết + nghỉ + 2 tiết)
      (1, 5) → "07:00–11:15"   (tiết 1-5 sáng)
      (6, 4) → "13:00–16:30"   (tiết 6-9 chiều)
      (6, 5) → "13:00–17:15"   (tiết 6-10 chiều)
    """
    PERIOD_MIN = 45
    BREAK_MIN  = 30

    def _offset(pos_in_session: int) -> int:
        """Minutes from session start to the START of period `pos_in_session` (1-based)."""
        if pos_in_session <= 2:
            return (pos_in_session - 1) * PERIOD_MIN
        # Break inserted after position 2
        return 2 * PERIOD_MIN + BREAK_MIN + (pos_in_session - 3) * PERIOD_MIN

    if start_period <= 5:
        session_start = 7 * 60   # 07:00
        pos = start_period
    else:
        session_start = 13 * 60  # 13:00
        pos = start_period - 5

    start_min = session_start + _offset(pos)
    end_min   = session_start + _offset(pos + num_periods - 1) + PERIOD_MIN

    def _fmt(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    return f"{_fmt(start_min)}–{_fmt(end_min)}"


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


def _format_weeks(weeks: list[WeekTimetable], start_index: int, max_weeks: int = 4) -> str:
    """Format a window of weeks into a compact string for the LLM / vector search.

    Window layout: 1 tuần trước + tuần hiện tại + 2 tuần tiếp theo (4 tuần tổng).
    - Tuần trước: context pattern (tuần nặng/nhẹ, so sánh)
    - Tuần hiện tại: hành động ngay hôm nay
    - 2 tuần tiếp: lập kế hoạch, cảnh báo deadline

    Empty weeks (nghỉ lễ/Tết) vẫn hiển thị trong phần forward (tương lai)
    nhưng KHÔNG tính vào slot khi tìm tuần trước — tìm lùi đến tuần có slot.
    """
    day_map = {2: "Thứ 2", 3: "Thứ 3", 4: "Thứ 4", 5: "Thứ 5", 6: "Thứ 6", 7: "Thứ 7", 8: "CN"}
    result = ""

    def _render_week(w: WeekTimetable, label: str = "") -> str:
        header_label = f" [{label}]" if label else ""
        if not w.slots:
            return f"Tuần {w.week_number}{header_label} ({w.start_date} - {w.end_date}): Không có lịch học\n\n"
        out = f"Tuần {w.week_number}{header_label} ({w.start_date} - {w.end_date}):\n"
        for s in w.slots:
            end_period = s.start_period + s.num_periods - 1
            cancelled = " [NGHỈ]" if s.is_cancelled else ""
            day_label = day_map.get(s.day_of_week, f"Thứ {s.day_of_week}")
            class_info = f" | Lớp: {s.class_name}" if s.class_name else ""
            time_range = _period_to_time(s.start_period, s.num_periods)
            out += (
                f"  {day_label} | {time_range} (Tiết {s.start_period}-{end_period}) | "
                f"{s.subject_name} | Phòng {s.room} | "
                f"GV: {s.lecturer}{class_info}{cancelled}\n"
            )
        out += "\n"
        return out

    # ── Tuần trước: tìm lùi đến tuần gần nhất có slot (bỏ qua tuần trống) ──
    prev_index = start_index - 1
    while prev_index >= 0 and not weeks[prev_index].slots:
        prev_index -= 1
    if prev_index >= 0:
        result += _render_week(weeks[prev_index], "TUẦN TRƯỚC")

    # ── Tuần hiện tại + các tuần tới (forward window) ────────────────────────
    shown = 0
    i = start_index
    while i < len(weeks) and shown < (max_weeks - 1):  # -1 vì đã dùng 1 slot cho tuần trước
        label = "TUẦN NÀY" if shown == 0 else ""
        result += _render_week(weeks[i], label)
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

    Trả về window 4 tuần: 1 tuần trước + tuần chứa `target_date` (hoặc tuần hiện tại) + 2 tuần tiếp.
    Tuần trước giúp agent nhận diện pattern, so sánh, và trả lời query về tuần vừa qua.
    Chỉ truyền semester_id khi muốn xem HK khác với HK hiện tại.

    Args:
        semester_id: Mã học kỳ (vd: 20252). Nếu None thì lấy HK hiện tại.
        target_date: Ngày cần xem lịch, định dạng YYYY-MM-DD (vd: "2026-03-10").
                     Nếu None thì dùng giờ thực của server nhà trường (Vietnam time).
        timetable_type: Loại TKB. 1=cá nhân (mặc định), 2=lớp sinh viên,
                        3=lớp, 4=môn học, 6=khoa quản lý sinh viên.

    Returns:
        Thời khóa biểu 4 tuần (1 trước + hiện tại + 2 tiếp): thứ, tiết, môn, phòng, lớp, giảng viên.
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
        header = f"Ngày tra cứu: {pivot.strftime('%d/%m/%Y')} | Tổng số tuần trong HK: {len(weeks)}\n"
        header += "Cửa sổ: 1 tuần trước + tuần hiện tại + 2 tuần tiếp theo\n\n"
        body = _format_weeks(weeks, start_index, max_weeks=4)

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


# ── Phase 2: New Tools ───────────────────────────────

@tool
async def get_student_info(
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Lấy thông tin cá nhân sinh viên: khoa, lớp, ngành, email trường, SĐT, cố vấn học tập.
    Dùng khi sinh viên hỏi về bản thân: "Tôi học khoa nào?", "Email trường tôi?", "CVHT tôi là ai?"

    Returns:
        Thông tin cá nhân: MSSV, tên, ngày sinh, lớp, khoa, ngành, email, SĐT, CVHT, trạng thái.
    """
    try:
        service = AcademicService(get_db())
        info = await service.get_student_info(user_id)

        result = f"MSSV: {info.mssv}\n"
        result += f"Họ tên: {info.full_name}\n"
        result += f"Ngày sinh: {info.date_of_birth} | Giới tính: {info.gender}\n"
        result += f"Lớp: {info.class_name}\n"
        result += f"Ngành: {info.major} | Bậc: {info.education_level}\n"
        result += f"Khoa: {info.department}\n"
        result += f"Email: {info.email}\n"
        result += f"SĐT: {info.phone}\n"
        if info.advisor_name:
            result += f"Cố vấn HT: {info.advisor_name}"
            if info.advisor_email:
                result += f" ({info.advisor_email})"
            if info.advisor_phone:
                result += f" - SĐT: {info.advisor_phone}"
            result += "\n"
        result += f"Trạng thái: {info.status}\n"
        result += f"Khóa: {info.semester_start} → {info.semester_end}\n"

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
            "message": f"Lỗi khi lấy thông tin SV ({type(e).__name__}): {str(e)}",
        }, ensure_ascii=False)


@tool
async def get_tuition_info(
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Xem tình hình học phí / công nợ tất cả các kỳ.
    Dùng khi sinh viên hỏi: "Tôi nợ học phí không?", "Học phí kỳ này bao nhiêu?", "Tổng đã đóng bao nhiêu?"

    Returns:
        Bảng học phí từng kỳ: phải thu, đã thu, còn nợ, đơn giá/tín chỉ.
    """
    try:
        service = AcademicService(get_db())
        semesters = await service.get_tuition_summary(user_id)

        if not semesters:
            return "Không có dữ liệu học phí."

        total_due = 0
        total_paid = 0
        total_remaining = 0

        result = f"Tổng: {len(semesters)} học kỳ\n\n"
        for s in semesters:
            due = int(s.amount_due) if s.amount_due.isdigit() else 0
            paid = int(s.amount_paid) if s.amount_paid.isdigit() else 0
            remaining = int(s.remaining) if s.remaining.isdigit() else 0
            total_due += due
            total_paid += paid
            total_remaining += remaining

            status_icon = "✅" if remaining == 0 else "⚠️"
            result += f"{status_icon} {s.semester_name}\n"
            result += f"  Phải thu: {due:,}đ | Đã thu: {paid:,}đ | Còn nợ: {remaining:,}đ\n"

        result += f"\n--- Tổng kết ---\n"
        result += f"Tổng phải thu: {total_due:,}đ\n"
        result += f"Tổng đã thu: {total_paid:,}đ\n"
        result += f"Tổng còn nợ: {total_remaining:,}đ\n"

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
            "message": f"Lỗi khi lấy học phí ({type(e).__name__}): {str(e)}",
        }, ensure_ascii=False)


@tool
async def get_semester_grades(
    semester_id: int,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Lấy kết quả học tập (điểm) của MỘT học kỳ cụ thể.
    Nhẹ hơn get_grades (chỉ lấy 1 kỳ thay vì tất cả).
    Dùng khi sinh viên hỏi: "Điểm kỳ này?", "Kỳ vừa rồi tôi được bao nhiêu điểm?"

    Args:
        semester_id: Mã học kỳ (vd: 20251). Nếu không biết, gọi get_semesters() trước.

    Returns:
        Danh sách môn học với số tín chỉ và điểm (hệ 10) trong học kỳ đó.
    """
    try:
        service = AcademicService(get_db())
        courses = await service.get_semester_result(user_id, semester_id)

        if not courses:
            return f"Không có dữ liệu điểm cho học kỳ {semester_id}."

        total_credits = sum(c.credits for c in courses)
        weighted_sum = sum(c.credits * c.score for c in courses)
        gpa = weighted_sum / total_credits if total_credits > 0 else 0

        result = f"Kết quả học kỳ {semester_id} ({len(courses)} môn, {total_credits:.0f} TC):\n"
        result += f"ĐTB ước tính (hệ 10): {gpa:.2f}\n\n"

        for c in courses:
            result += f"  {c.subject_name} ({c.credits:.0f} TC): {c.score}/10\n"

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
            "message": f"Lỗi khi lấy điểm HK ({type(e).__name__}): {str(e)}",
        }, ensure_ascii=False)


@tool
async def get_semester_timetable_overview(
    semester_id: int | None = None,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Xem tổng quan thời khóa biểu CẢ học kỳ: danh sách các môn, số tín chỉ, giảng viên, phòng học.
    Khác với get_timetable (xem theo tuần), tool này cho cái nhìn TOÀN CẢNH cả kỳ.
    Dùng khi: "Kỳ này học mấy môn?", "Ai dạy môn X?", "Tổng bao nhiêu tín chỉ kỳ này?"

    Args:
        semester_id: Mã học kỳ (vd: 20251). Nếu None, gọi get_semesters() để lấy kỳ hiện tại trước.

    Returns:
        Danh sách môn trong kỳ: tên, TC, nhóm/tổ, GV, phòng, thứ, tiết, thời gian, lớp.
    """
    try:
        service = AcademicService(get_db())

        # Resolve semester if not provided
        actual_semester = semester_id
        if not actual_semester:
            client = await service._get_authenticated_client(user_id)
            try:
                sdata = await client.get_semesters()
                actual_semester = sdata.get("hoc_ky_theo_ngay_hien_tai")
            finally:
                await client.close()

        if not actual_semester:
            return "Không xác định được học kỳ hiện tại. Hãy truyền semester_id."

        data = await service.get_semester_timetable_overview(user_id, int(actual_semester))
        raw_classes = data.get("ds_nhom_to", [])

        if not raw_classes:
            return f"Không có dữ liệu TKB cho học kỳ {actual_semester}."

        # Group by subject (ma_mon) to condense output
        day_map = {2: "T2", 3: "T3", 4: "T4", 5: "T5", 6: "T6", 7: "T7", 8: "CN"}
        subjects: dict = {}
        for c in raw_classes:
            key = c.get("ma_mon", "")
            if key not in subjects:
                subjects[key] = {
                    "ten_mon": c.get("ten_mon", ""),
                    "so_tc": c.get("so_tc", "?"),
                    "nhom_to": c.get("nhom_to", ""),
                    "gv": c.get("gv", ""),
                    "lop": c.get("lop", ""),
                    "sessions": [],
                }
            # Track unique sessions by (thu, tbd, phong, tkb)
            session_key = (c.get("thu"), c.get("tbd"), c.get("phong"), c.get("tkb"))
            if session_key not in [
                (s["thu"], s["tbd"], s["phong"], s["tkb"])
                for s in subjects[key]["sessions"]
            ]:
                subjects[key]["sessions"].append({
                    "thu": c.get("thu"),
                    "tbd": c.get("tbd"),
                    "so_tiet": c.get("so_tiet"),
                    "tu_gio": c.get("tu_gio", ""),
                    "den_gio": c.get("den_gio", ""),
                    "phong": c.get("phong", ""),
                    "tkb": c.get("tkb", ""),
                })

        total_tc = sum(float(s["so_tc"]) for s in subjects.values() if s["so_tc"] != "?")
        result = f"TKB tổng quan HK {actual_semester}: {len(subjects)} môn, ~{total_tc:.0f} TC\n\n"

        for ma_mon, info in subjects.items():
            result += f"• {info['ten_mon']} ({info['so_tc']} TC) | Nhóm: {info['nhom_to']} | GV: {info['gv']}\n"
            for s in info["sessions"][:3]:  # Limit sessions shown
                day_label = day_map.get(s["thu"], f"T{s['thu']}")
                result += f"  {day_label} tiết {s['tbd']} ({s['tu_gio']}-{s['den_gio']}) P.{s['phong']} [{s['tkb']}]\n"
            if len(info["sessions"]) > 3:
                result += f"  ... và {len(info['sessions']) - 3} buổi khác\n"

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
            "message": f"Lỗi khi lấy TKB tổng quan ({type(e).__name__}): {str(e)}",
        }, ensure_ascii=False)


# Export all tools for the agent graph
academic_tools = [
    get_semesters, get_timetable, get_grades,
    get_student_info, get_tuition_info,
    get_semester_grades, get_semester_timetable_overview,
]
