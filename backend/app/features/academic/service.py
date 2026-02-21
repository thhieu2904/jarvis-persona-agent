"""
Academic feature: Service layer for syncing and caching school data.
"""

from datetime import datetime, timezone, timedelta
from supabase import Client

from app.config import get_settings
from app.core.security import encrypt_value, decrypt_value
from app.features.academic.school_client import SchoolAPIClient
from app.features.academic.schemas import (
    TimetableSlot,
    WeekTimetable,
    GradeEntry,
    SemesterGrades,
)


class AcademicService:
    """
    Manages school data syncing with cache-first strategy.
    
    Flow: Tool call → Check DB cache → If stale, sync from school API → Return data
    """

    def __init__(self, db: Client):
        self.db = db
        self.settings = get_settings()

    # ── Credential Management ────────────────────────────

    async def save_credentials(self, user_id: str, mssv: str, password: str):
        """Encrypt and save school credentials."""
        encrypted_user = encrypt_value(mssv)
        encrypted_pass = encrypt_value(password)

        # Upsert: update if exists, insert if not
        self.db.table("user_credentials").upsert(
            {
                "user_id": user_id,
                "school_username_enc": encrypted_user.decode("latin-1"),
                "school_password_enc": encrypted_pass.decode("latin-1"),
            },
            on_conflict="user_id",
        ).execute()

    async def reconnect_credentials(self, user_id: str, mssv: str, password: str):
        """Re-connect: delete old credentials and save new ones.
        
        Used when user loses their encryption key or wants to update credentials.
        """
        # Delete old record
        self.db.table("user_credentials").delete().eq("user_id", user_id).execute()
        # Save new
        await self.save_credentials(user_id, mssv, password)

    async def _get_authenticated_client(self, user_id: str) -> SchoolAPIClient:
        """Create a SchoolAPIClient and login using stored credentials.
        
        Login flow: GET /api/pn-signin → 302 redirect → extract JWT access_token
        from CurrUser param → set as Bearer token for all subsequent POST API calls.
        
        Each sync operation creates a fresh client, logs in, fetches data, then closes.
        
        Returns:
            Authenticated SchoolAPIClient with Bearer token set.
            
        Raises:
            ValueError: If no credentials stored or login fails.
        """
        record = (
            self.db.table("user_credentials")
            .select("*")
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if not record.data:
            raise ValueError("Chưa kết nối tài khoản trường. Vui lòng cài đặt trong Profile.")

        cred = record.data

        # Decrypt stored credentials
        mssv = decrypt_value(cred["school_username_enc"].encode("latin-1"))
        password = decrypt_value(cred["school_password_enc"].encode("latin-1"))

        # Create client and login (sets session cookies internally)
        client = SchoolAPIClient()
        await client.login(mssv, password)

        # Update last login timestamp
        self.db.table("user_credentials").update(
            {"last_login_at": datetime.now(timezone.utc).isoformat()}
        ).eq("user_id", user_id).execute()

        return client

    # ── Cache Layer ──────────────────────────────────────

    async def _get_cached(self, user_id: str, data_type: str, semester: str | None = None) -> dict | None:
        """Get cached data if fresh (within TTL)."""
        query = (
            self.db.table("academic_sync_cache")
            .select("*")
            .eq("user_id", user_id)
            .eq("data_type", data_type)
        )
        if semester:
            query = query.eq("semester", semester)

        result = query.execute()

        if not result.data:
            return None

        record = result.data[0]
        last_synced = datetime.fromisoformat(record["last_synced_at"])
        ttl = timedelta(hours=self.settings.SCHOOL_CACHE_TTL_HOURS)

        if datetime.now(timezone.utc) - last_synced < ttl:
            return record["raw_data"]

        return None  # Cache stale

    async def _update_cache(
        self, user_id: str, data_type: str, data: dict, semester: str | None = None
    ):
        """Upsert cached data."""
        self.db.table("academic_sync_cache").upsert(
            {
                "user_id": user_id,
                "data_type": data_type,
                "semester": semester,
                "raw_data": data,
                "last_synced_at": datetime.now(timezone.utc).isoformat(),
                "sync_status": "success",
                "sync_error": None,
            },
            on_conflict="user_id,data_type,semester",
        ).execute()

    # ── Data Access (Cache-first) ────────────────────────

    async def get_timetable(self, user_id: str, semester: str | None = None) -> list[WeekTimetable]:
        """Get weekly timetable. Cache-first, sync from school API if stale."""
        # 1. Check cache
        cached = await self._get_cached(user_id, "timetable", semester)
        if cached:
            raw_weeks = cached.get("ds_tuan_tkb", [])
        else:
            # 2. Sync from school (login + fetch + close)
            client = await self._get_authenticated_client(user_id)
            try:
                data = await client.get_weekly_timetable(
                    int(semester) if semester else None,
                )
                await self._update_cache(user_id, "timetable", data, semester)
                raw_weeks = data.get("ds_tuan_tkb", [])
            finally:
                await client.close()

        # 3. Transform to clean models
        return self._parse_timetable(raw_weeks)

    async def get_grades(self, user_id: str) -> list[SemesterGrades]:
        """Get all grades. Cache-first, sync from school API if stale."""
        cached = await self._get_cached(user_id, "grades")
        if cached:
            raw_semesters = cached.get("ds_diem_hocky", [])
        else:
            client = await self._get_authenticated_client(user_id)
            try:
                data = await client.get_grades()
                await self._update_cache(user_id, "grades", data)
                raw_semesters = data.get("ds_diem_hocky", [])
            finally:
                await client.close()

        return self._parse_grades(raw_semesters)

    # ── Data Transformers ────────────────────────────────

    @staticmethod
    def _parse_timetable(raw_weeks: list) -> list[WeekTimetable]:
        """Transform raw school API TKB data into clean models."""
        weeks = []
        for w in raw_weeks:
            slots = []
            for s in w.get("ds_thoi_khoa_bieu", []):
                slots.append(TimetableSlot(
                    day_of_week=s.get("thu_kieu_so", 0),
                    start_period=s.get("tiet_bat_dau", 0),
                    num_periods=s.get("so_tiet", 0),
                    subject_code=s.get("ma_mon", ""),
                    subject_name=s.get("ten_mon", ""),
                    subject_name_en=s.get("ten_mon_eg", ""),
                    credits=s.get("so_tin_chi", ""),
                    lecturer=s.get("ten_giang_vien", ""),
                    room=s.get("ma_phong", ""),
                    class_name=s.get("ten_lop", ""),
                    date=s.get("ngay_hoc", ""),
                    is_cancelled=s.get("is_nghi_day", False),
                ))
            
            weeks.append(WeekTimetable(
                week_number=w.get("tuan_hoc_ky", 0),
                start_date=w.get("ngay_bat_dau", ""),
                end_date=w.get("ngay_ket_thuc", ""),
                slots=slots,
            ))
        return weeks

    @staticmethod
    def _parse_grades(raw_semesters: list) -> list[SemesterGrades]:
        """Transform raw school API grades data into clean models."""
        semesters = []
        for sem in raw_semesters:
            courses = []
            for c in sem.get("ds_diem_mon_hoc", []):
                courses.append(GradeEntry(
                    subject_code=c.get("ma_mon", ""),
                    subject_name=c.get("ten_mon", ""),
                    subject_name_en=c.get("ten_mon_eg", ""),
                    credits=c.get("so_tin_chi", ""),
                    grade_10=c.get("diem_tk", ""),
                    grade_4=c.get("diem_tk_so", ""),
                    grade_letter=c.get("diem_tk_chu", ""),
                    result=c.get("ket_qua", 0),
                    component_scores=c.get("ds_diem_thanh_phan", []),
                ))

            semesters.append(SemesterGrades(
                semester_code=sem.get("hoc_ky", ""),
                semester_name=sem.get("ten_hoc_ky", ""),
                gpa_10=sem.get("dtb_hk_he10", ""),
                gpa_4=sem.get("dtb_hk_he4", ""),
                cumulative_gpa_10=sem.get("dtb_tich_luy_he_10", ""),
                cumulative_gpa_4=sem.get("dtb_tich_luy_he_4", ""),
                credits_earned=sem.get("so_tin_chi_dat_hk", ""),
                classification=sem.get("xep_loai_tkb_hk", ""),
                courses=courses,
            ))
        return semesters
