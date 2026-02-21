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
    """Lưu (mã hóa) thông tin đăng nhập trường."""
    service = AcademicService(db)
    await service.save_credentials(user_id, data.mssv, data.password)
    return {"message": "Đã lưu thông tin đăng nhập trường thành công"}


@router.post("/reconnect")
async def reconnect_credentials(
    data: SchoolCredentialsRequest,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Re-connect: Xóa credentials cũ và lưu mới (khi mất key hoặc đổi mật khẩu)."""
    service = AcademicService(db)
    await service.reconnect_credentials(user_id, data.mssv, data.password)
    return {"message": "Đã kết nối lại tài khoản trường thành công"}


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
    """Trigger manual sync từ school API."""
    # TODO: Implement manual sync trigger (invalidate cache)
    return {"message": f"Sync triggered for {data_type}", "status": "pending"}
