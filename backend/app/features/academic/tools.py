"""
Academic tools for the agent — connected to REAL SchoolAPIClient.
These are LangChain @tool functions that the LangGraph agent can call.
"""

import json
import asyncio
from langchain_core.tools import tool

from app.features.academic.school_client import SchoolAPIClient


# ── Module-level client (reused across tool calls in same session) ──
_client: SchoolAPIClient | None = None


async def _get_client() -> SchoolAPIClient:
    """Get or create an authenticated SchoolAPIClient.
    
    TODO: In production, credentials come from DB (encrypted).
    For now, hardcoded for development testing.
    """
    global _client
    if _client is None or not _client.is_authenticated:
        from app.config import get_settings
        _client = SchoolAPIClient()
        # TODO: Replace with credential lookup from Supabase
        await _client.login("110122221", "290406")
    return _client


@tool
async def get_semesters() -> str:
    """Lấy danh sách tất cả các học kỳ của sinh viên.
    Dùng khi cần biết danh sách học kỳ, học kỳ hiện tại, hoặc mã học kỳ để tra cứu.
    
    Returns:
        Danh sách học kỳ bao gồm: mã HK, tên HK, ngày bắt đầu/kết thúc.
    """
    client = await _get_client()
    data = await client.get_semesters()

    # Format for LLM consumption
    current = data.get("hoc_ky_theo_ngay_hien_tai", "?")
    semesters = data.get("ds_hoc_ky", [])

    result = f"Hoc ky hien tai: {current}\n"
    result += f"Tong so hoc ky: {len(semesters)}\n\n"
    for s in semesters[:6]:  # Limit to recent 6
        result += f"- {s.get('ten_hoc_ky', '?')} (ma: {s.get('hoc_ky', '?')})\n"

    return result


@tool
async def get_timetable(semester_id: int | None = None) -> str:
    """Lấy thời khóa biểu (TKB) / lịch học theo tuần.
    Dùng khi sinh viên hỏi về lịch học, thời gian học, phòng học, hoặc giảng viên.
    
    Args:
        semester_id: Mã học kỳ (vd: 20252). Nếu None thì lấy HK hiện tại.
    
    Returns:
        Thời khóa biểu theo tuần: thứ, tiết, môn, phòng, giảng viên.
    """
    client = await _get_client()
    data = await client.get_weekly_timetable(semester_id)

    weeks = data.get("ds_tuan_tkb", [])
    if not weeks:
        return "Khong co thoi khoa bieu cho hoc ky nay (co the HK chua bat dau)."

    result = f"Tong so tuan: {len(weeks)}\n\n"
    for w in weeks[:3]:  # Show first 3 weeks
        result += f"Tuan {w.get('tuan_hoc_ky', '?')} ({w.get('ngay_bat_dau', '?')} - {w.get('ngay_ket_thuc', '?')}):\n"
        for s in w.get("ds_thoi_khoa_bieu", []):
            day = s.get("thu_kieu_so", "?")
            result += (
                f"  Thu {day} | Tiet {s.get('tiet_bat_dau', '?')}-{s.get('tiet_bat_dau', 0) + s.get('so_tiet', 0) - 1} | "
                f"{s.get('ten_mon', '?')} | Phong {s.get('ma_phong', '?')} | "
                f"GV: {s.get('ten_giang_vien', '?')}\n"
            )
        result += "\n"

    return result


@tool
async def get_grades() -> str:
    """Lấy bảng điểm tất cả các học kỳ.
    Dùng khi sinh viên hỏi về điểm số, GPA, kết quả học tập, hoặc xếp loại.
    
    Returns:
        Bảng điểm theo HK: GPA, điểm từng môn, xếp loại, tín chỉ.
    """
    client = await _get_client()
    data = await client.get_grades()

    semesters = data.get("ds_diem_hocky", [])
    if not semesters:
        return "Khong co du lieu diem."

    result = f"Tong so hoc ky co diem: {len(semesters)}\n\n"

    for sem in semesters[:3]:  # Show latest 3 semesters
        result += f"--- {sem.get('ten_hoc_ky', '?')} ---\n"
        result += f"GPA HK: {sem.get('dtb_hk_he10', '?')} (he 10) / {sem.get('dtb_hk_he4', '?')} (he 4)\n"
        result += f"GPA Tich luy: {sem.get('dtb_tich_luy_he_10', '?')} (he 10) / {sem.get('dtb_tich_luy_he_4', '?')} (he 4)\n"
        result += f"Tin chi dat HK: {sem.get('so_tin_chi_dat_hk', '?')}\n"
        result += f"Xep loai: {sem.get('xep_loai_tkb_hk', '?')}\n"
        
        courses = sem.get("ds_diem_mon_hoc", [])
        for c in courses:
            result += (
                f"  {c.get('ten_mon', '?')} ({c.get('so_tin_chi', '?')} TC): "
                f"{c.get('diem_tk', '?')} - {c.get('diem_tk_chu', '?')}\n"
            )
        result += "\n"

    return result


# Export all tools for the agent graph
academic_tools = [get_semesters, get_timetable, get_grades]
