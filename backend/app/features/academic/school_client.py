"""
Academic feature: School API client for TVU (ttsv.tvu.edu.vn).

AUTHENTICATION (verified by live testing):
  1. Build JSON: {"username": MSSV, "password": pass, "uri": "https://ttsv.tvu.edu.vn/#/"}
  2. Base64-encode the JSON → code param
  3. GET /api/pn-signin?code=[base64] — DO NOT follow redirects
  4. Server responds 302 with Location header containing CurrUser=[base64_json]
  5. Decode CurrUser → extract "access_token" (JWE, ~1359 chars)
  6. All data APIs: POST with Authorization: Bearer <access_token>

DATA ENDPOINTS:
  1. Semesters:         POST /public/api/sch/w-locdshockytkbuser
  2. TKB:               POST /public/api/sch/w-locdstkbtuanusertheohocky
                             body: {hoc_ky, loai_doi_tuong}  (1=cá nhân, 2=lớp SV, 3=lớp, 4=môn, 6=khoa)
  3. Grades:            POST /public/api/srm/w-locdsdiemsinhvien
  4. Auth cfg:          GET  /public/api/auth/authconfig
  5. Server time:       GET  /public/api/hsba/w-gettimeserver        (NO auth, Vietnam time)
  6. TKB object types:  POST /public/api/sch/w-locdsdoituongthoikhoabieu (NO auth)
"""

import json
import base64
from datetime import datetime
from urllib.parse import urlparse, unquote
import httpx

from app.config import get_settings


class SchoolAPIClient:
    """Client for TVU student portal API.
    
    Auth: GET login → extract JWT from redirect URL → Bearer token for all POST APIs.
    """

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.SCHOOL_API_BASE_URL.rstrip("/")
        self.root_url = "https://ttsv.tvu.edu.vn"
        self._access_token: str | None = None
        self._user_info: dict = {}
        self._timeout = settings.SCHOOL_API_TIMEOUT

        # Client for data APIs (with Bearer auth, follows redirects)
        self._client = httpx.AsyncClient(
            timeout=float(self._timeout),
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
            },
        )

    # ── Authentication ───────────────────────────────────

    async def login(self, mssv: str, password: str) -> str:
        """Authenticate with school portal.
        
        Flow:
          1. Build JSON → Base64 encode → GET /api/pn-signin?code=...
          2. Capture 302 redirect Location header
          3. Extract CurrUser from fragment → decode Base64 → get access_token
          4. Store token for subsequent API calls
        
        Args:
            mssv: Student ID (e.g., "110122221")
            password: Password
            
        Returns:
            access_token string (JWE, ~1359 chars)
            
        Raises:
            ValueError: If login fails or token extraction fails.
        """
        # Step 1: Build Base64 code
        payload = json.dumps({
            "username": mssv,
            "password": password,
            "uri": f"{self.root_url}/#/",
        }, separators=(",", ":"))
        code = base64.b64encode(payload.encode()).decode()

        # Step 2: GET with NO redirect following (we need the 302 Location)
        async with httpx.AsyncClient(
            timeout=float(self._timeout),
            follow_redirects=False,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as login_client:
            response = await login_client.get(
                f"{self.root_url}/api/pn-signin",
                params={"code": code},
            )

        if response.status_code != 302:
            raise ValueError(
                f"Login failed: expected 302 redirect, got {response.status_code}. "
                f"Check MSSV and password."
            )

        # Step 3: Extract CurrUser from redirect URL fragment
        location = response.headers.get("location", "")
        token = self._extract_token_from_redirect(location)

        if not token:
            raise ValueError(
                "Login failed: could not extract access_token from redirect URL."
            )

        # Step 4: Store token and update client headers + cookies
        self._access_token = token
        self._client.headers["Authorization"] = f"Bearer {token}"

        # Transfer session cookies from login response (ASP.NET_SessionId etc.)
        # The school server requires both Bearer token AND session cookies for data APIs.
        for name, value in response.cookies.items():
            self._client.cookies.set(name, value)

        # Follow the redirect to establish full session (sets additional cookies)
        redirect_url = response.headers.get("location", "")
        if redirect_url:
            try:
                await self._client.get(redirect_url)
            except Exception:
                pass  # Best effort — token + initial cookies should be enough

        return token

    def _extract_token_from_redirect(self, location: str) -> str | None:
        """Extract access_token from the 302 redirect URL.
        
        The redirect URL looks like:
          http://ttsv.tvu.edu.vn/#/?CurrUser=<base64_json>&gopage=
        
        CurrUser decodes to JSON containing {access_token, userName, roles, ...}
        """
        try:
            parsed = urlparse(location)
            fragment = parsed.fragment  # /?CurrUser=...&gopage=

            if "CurrUser=" not in fragment:
                return None

            # Extract CurrUser value
            curr_user_encoded = fragment.split("CurrUser=")[1].split("&")[0]
            curr_user_decoded = unquote(curr_user_encoded)

            # Add Base64 padding if needed
            padding = 4 - len(curr_user_decoded) % 4
            if padding != 4:
                curr_user_decoded += "=" * padding

            # Decode and parse JSON
            user_data = json.loads(base64.b64decode(curr_user_decoded))
            self._user_info = {
                "name": user_data.get("FullName", ""),
                "username": user_data.get("userName", ""),
                "roles": user_data.get("roles", ""),
            }

            return user_data.get("access_token")

        except Exception:
            return None

    @property
    def is_authenticated(self) -> bool:
        """Check if client has a valid access token."""
        return self._access_token is not None

    @property
    def user_info(self) -> dict:
        """User info extracted from login (name, username, roles)."""
        return self._user_info

    # ── Data APIs (all POST) ─────────────────────────────

    async def get_semesters(self) -> dict:
        """Get list of all semesters (hoc ky).
        
        POST /public/api/sch/w-locdshockytkbuser
        """
        self._ensure_authenticated()
        response = await self._client.post(
            f"{self.base_url}/sch/w-locdshockytkbuser",
            json={},
        )
        response.raise_for_status()
        return self._extract_data(response)

    async def get_weekly_timetable(
        self,
        semester_id: int | None = None,
        timetable_type: int = 1,
    ) -> dict:
        """Get weekly timetable (TKB) for a semester.

        POST /public/api/sch/w-locdstkbtuanusertheohocky

        Args:
            semester_id: e.g., 20252. If None, uses current semester.
            timetable_type: Object type filter.
                1 = Cá nhân (default)
                2 = Lớp sinh viên
                3 = Lớp
                4 = Môn học
                6 = Khoa quản lý sinh viên
        """
        self._ensure_authenticated()
        
        # The school API requires the parameters to be wrapped in a "filter" object
        # Otherwise it throws NullReferenceException in W_LocDSTKBDangTuanTheoSinhVienHoacGiangVien
        filter_data: dict = {}
        if semester_id:
            filter_data["hoc_ky"] = semester_id
        
        # Only send loai_doi_tuong for non-default types (1 = cá nhân).
        if timetable_type and timetable_type != 1:
            filter_data["loai_doi_tuong"] = timetable_type

        # Wrap in {"filter": ...}
        body = {"filter": filter_data}

        response = await self._client.post(
            f"{self.base_url}/sch/w-locdstkbtuanusertheohocky",
            json=body,
        )
        response.raise_for_status()
        return self._extract_data(response)

    async def get_grades(self, by_tkb: bool = False) -> dict:
        """Get all grades across semesters.
        
        POST /public/api/srm/w-locdsdiemsinhvien
        """
        self._ensure_authenticated()
        response = await self._client.post(
            f"{self.base_url}/srm/w-locdsdiemsinhvien",
            json={"hien_thi_mon_theo_hkdk": by_tkb},
        )
        response.raise_for_status()
        return self._extract_data(response)

    async def get_auth_config(self) -> dict:
        """Get auth config (this one is actually GET).

        GET /public/api/auth/authconfig
        """
        response = await self._client.get(
            f"{self.base_url}/auth/authconfig",
        )
        response.raise_for_status()
        return self._extract_data(response)

    # ── Public endpoints (no auth required) ─────────────

    @classmethod
    async def get_server_time(cls) -> datetime:
        """Get current Vietnam server time from school portal.

        GET /public/api/hsba/w-gettimeserver  — no auth required.

        Returns:
            datetime in Vietnam time (no tzinfo; school does not include offset).
            Falls back to datetime.now() if request fails.

        Response: {"thoigianht": "23/02/2026 00:26:37"}
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://ttsv.tvu.edu.vn/public/api/hsba/w-gettimeserver"
                )
                response.raise_for_status()
                raw = response.json().get("thoigianht", "")
                return datetime.strptime(raw, "%d/%m/%Y %H:%M:%S")
        except Exception:
            return datetime.now()

    @classmethod
    async def get_timetable_types(cls) -> list[dict]:
        """Get available timetable object types.

        POST /public/api/sch/w-locdsdoituongthoikhoabieu  — no auth required.

        Returns list of {loai_doi_tuong: int, ten_doi_tuong: str}.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    "https://ttsv.tvu.edu.vn/public/api/sch/w-locdsdoituongthoikhoabieu",
                    json={},
                )
                response.raise_for_status()
                data = response.json().get("data", {})
                return data.get("ds_doi_tuong_tkb", [])
        except Exception:
            return []

    # ── Helpers ──────────────────────────────────────────

    def _ensure_authenticated(self):
        """Raise if not logged in."""
        if not self.is_authenticated:
            raise ValueError("Chua dang nhap. Goi login() truoc.")

    @staticmethod
    def _extract_data(response: httpx.Response) -> dict:
        """Extract 'data' from API response JSON."""
        try:
            body = response.json()
            return body.get("data", body)
        except Exception:
            return {"raw": response.text}

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
