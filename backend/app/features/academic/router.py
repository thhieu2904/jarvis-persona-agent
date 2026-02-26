"""
Academic feature: API routes for school data and credentials.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.dependencies import get_db, get_current_user_id
from app.features.academic.schemas import SchoolCredentialsRequest, SyncStatusResponse
from app.features.academic.service import AcademicService

router = APIRouter()


@router.put("/credentials")
async def save_credentials(
    data: SchoolCredentialsRequest,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Lưu (mã hóa) thông tin đăng nhập trường sau khi kiểm tra."""
    service = AcademicService(db)
    try:
        await service.save_credentials(user_id, data.mssv, data.password)
        return {"message": "Đã kết nối và lưu thông tin trường thành công"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ConnectionError as e:
        # Pass back a specific 504 for timeout / 502 for bad gateway if needed, but 503 is good.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.post("/reconnect")
async def reconnect_credentials(
    data: SchoolCredentialsRequest,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Re-connect: Xóa credentials cũ và lưu mới (khi mất key hoặc đổi mật khẩu)."""
    service = AcademicService(db)
    try:
        await service.reconnect_credentials(user_id, data.mssv, data.password)
        return {"message": "Đã kết nối lại tài khoản trường thành công"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.get("/timetable")
async def get_timetable(
    semester: str | None = None,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Lấy thời khóa biểu (cache-first, auto-sync)."""
    service = AcademicService(db)
    try:
        result = await service.get_timetable(user_id, semester)
        return {"data": [w.model_dump() for w in result]}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/grades")
async def get_grades(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Lấy bảng điểm tất cả học kỳ (cache-first, auto-sync)."""
    service = AcademicService(db)
    try:
        result = await service.get_grades(user_id)
        return {"data": [s.model_dump() for s in result]}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sync")
async def trigger_sync(
    data_type: str = "all",
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Trigger manual sync từ school API.
    
    Args:
        data_type: 'timetable', 'grades', or 'all' (default).
    """
    service = AcademicService(db)
    
    valid_types = ["timetable", "grades", "all"]
    if data_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"data_type phải là một trong: {', '.join(valid_types)}",
        )

    # Invalidate cache
    if data_type == "all":
        db.table("academic_sync_cache").delete().eq("user_id", user_id).execute()
    else:
        db.table("academic_sync_cache").delete().eq(
            "user_id", user_id
        ).eq("data_type", data_type).execute()

    # Re-sync by fetching fresh data (this populates cache)
    synced = []
    errors = []

    try:
        if data_type in ("timetable", "all"):
            await service.get_timetable(user_id)
            synced.append("timetable")
    except Exception as e:
        errors.append({"type": "timetable", "error": str(e)})

    try:
        if data_type in ("grades", "all"):
            await service.get_grades(user_id)
            synced.append("grades")
    except Exception as e:
        errors.append({"type": "grades", "error": str(e)})

    return {
        "message": f"Sync hoàn tất",
        "synced": synced,
        "errors": errors if errors else None,
    }


@router.delete("/cache")
async def clear_cache(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Xóa toàn bộ dữ liệu tạm (cache) của user hiện tại.
    
    Dùng khi user muốn chủ động xóa sạch dữ liệu học tập đã lưu tạm.
    """
    result = db.table("academic_sync_cache").delete().eq("user_id", user_id).execute()
    count = len(result.data) if result.data else 0
    return {
        "message": f"Đã xóa {count} bản ghi cache.",
        "deleted_count": count,
    }
