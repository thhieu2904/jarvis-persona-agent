"""
Academic feature: Schemas for request/response models.
"""

from pydantic import BaseModel
from datetime import datetime


class SchoolCredentialsRequest(BaseModel):
    """Request to save/update school login credentials."""
    mssv: str
    password: str


class SyncStatusResponse(BaseModel):
    """Response showing sync status for cached data."""
    data_type: str
    semester: str | None = None
    sync_status: str
    last_synced_at: datetime | None = None
    sync_error: str | None = None


class TimetableSlot(BaseModel):
    """A single timetable entry."""
    day_of_week: int          # 2=Mon, 3=Tue, ..., 7=Sat, 8=Sun
    start_period: int         # Tiết bắt đầu
    num_periods: int          # Số tiết
    subject_code: str
    subject_name: str
    subject_name_en: str
    credits: str
    lecturer: str
    room: str
    class_name: str
    date: str                 # ISO date
    is_cancelled: bool = False


class WeekTimetable(BaseModel):
    """Timetable for one week."""
    week_number: int
    start_date: str
    end_date: str
    slots: list[TimetableSlot]


class GradeEntry(BaseModel):
    """A single course grade."""
    subject_code: str
    subject_name: str
    subject_name_en: str
    credits: str
    grade_10: str             # Điểm hệ 10
    grade_4: str              # Điểm hệ 4
    grade_letter: str         # A, B+, B, C+, ...
    result: int               # 1=passed, 0=pending
    component_scores: list[dict] = []


class SemesterGrades(BaseModel):
    """Grades for one semester."""
    semester_code: str
    semester_name: str
    gpa_10: str               # ĐTB HK hệ 10
    gpa_4: str                # ĐTB HK hệ 4
    cumulative_gpa_10: str    # ĐTB tích lũy hệ 10
    cumulative_gpa_4: str     # ĐTB tích lũy hệ 4
    credits_earned: str
    classification: str       # "Giỏi", "Khá", "Xuất sắc"
    courses: list[GradeEntry]


# ── Phase 2: New models ─────────────────────────────

class StudentInfo(BaseModel):
    """Student personal information from w-locsinhvieninfo."""
    mssv: str
    full_name: str
    date_of_birth: str
    gender: str
    class_name: str           # Lớp (e.g. "DA24KTB")
    department: str           # Khoa (e.g. "Trường Kinh tế, Luật")
    major: str                # Ngành (e.g. "Kế toán")
    education_level: str      # Bậc hệ đào tạo (e.g. "đại học")
    email: str
    phone: str
    advisor_name: str         # Cố vấn học tập
    advisor_email: str
    advisor_phone: str
    status: str               # Hiện diện (e.g. "Đang học")
    semester_start: str       # HK vào (e.g. "Học kỳ 1 Năm học 2024-2025")
    semester_end: str         # HK ra dự kiến


class TuitionSemester(BaseModel):
    """Tuition info for one semester from w-locdstonghophocphisv."""
    semester_code: int        # nhhk (e.g. 20251)
    semester_name: str        # ten_hoc_ky
    tuition: str              # hoc_phi
    discount: str             # mien_giam
    amount_due: str           # phai_thu
    amount_paid: str          # da_thu
    remaining: str            # con_no
    unit_price: str           # don_gia (per credit)


class SemesterCourseResult(BaseModel):
    """A course result from w-inketquahoctap (single semester)."""
    subject_code: str         # ma_doi_tuong
    subject_name: str         # ten_doi_tuong
    credits: float            # diem_trung_binh1 (so_tin_chi in this API)
    score: float              # diem_trung_binh2 (điểm/10)

