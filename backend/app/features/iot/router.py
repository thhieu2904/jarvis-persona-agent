from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
import logging
import tinytuya

from app.core.dependencies import get_current_user_id
from app.core.database import get_supabase_client
from supabase import Client

# Chúng ta sẽ queries bằng DB API của Supabase (hoặc SQLAlchemy tùy design chung)
# Ở dự án này, auth qua Supabase nên get_current_user trả về dict
from app.features.iot.schemas import IoTDeviceCreate, IoTDeviceUpdate, IoTDeviceResponse, IoTDeviceTestRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iot/devices", tags=["IoT Devices"])

@router.get("/scan")
def scan_lan_devices(
    timeout: int = 5,
    user_id: str = Depends(get_current_user_id)
):
    """Quét mạng LAN (Broadcast UDP) để tìm kiếm các thiết bị Tuya tự động."""
    try:
        logging.info(f"Bắt đầu quét mạng LAN (Timeout: {timeout}s)...")
        # deviceScan() map object: IP -> { 'ip': .., 'gwId': .., 'active': .., 'version': .. }
        # Note: gwId thường chính là device_id của Tuya.
        devices = tinytuya.deviceScan(False, timeout)
        
        found_list = []
        for ip, info in devices.items():
            found_list.append({
                "ip": info.get("ip"),
                "device_id": info.get("id") or info.get("gwId"),
                "version": info.get("version"),
                "product_key": info.get("productKey"),
                "mac": info.get("mac")
            })
            
        return {
            "success": True,
            "count": len(found_list),
            "devices": found_list
        }
    except Exception as e:
        logging.error(f"Lỗi khi scan mạng LAN: {e}")
        return {"success": False, "message": str(e), "devices": []}

@router.get("", response_model=List[IoTDeviceResponse])
def get_user_iot_devices(
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase_client)
):
    """Lấy danh sách thiết bị IoT của người dùng."""
    response = supabase.table("iot_devices").select("*").eq("user_id", user_id).execute()
    return response.data

@router.post("", response_model=IoTDeviceResponse, status_code=status.HTTP_201_CREATED)
def create_iot_device(
    device_in: IoTDeviceCreate,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase_client)
):
    """Thêm một thiết bị IoT mới."""
    data_to_insert = device_in.model_dump()
    data_to_insert["user_id"] = user_id
    
    response = supabase.table("iot_devices").insert(data_to_insert).execute()
    if not response.data:
        raise HTTPException(status_code=400, detail="Không thể tạo thiết bị.")
    return response.data[0]

@router.patch("/{device_id}", response_model=IoTDeviceResponse)
def update_iot_device(
    device_id: UUID,
    device_in: IoTDeviceUpdate,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase_client)
):
    """Cập nhật cấu hình thiết bị IoT."""
    update_data = device_in.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided.")
        
    response = supabase.table("iot_devices").update(update_data).eq("id", str(device_id)).eq("user_id", user_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị hoặc không có quyền sửa.")
    return response.data[0]

@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_iot_device(
    device_id: UUID,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase_client)
):
    """Xóa một thiết bị IoT."""
    response = supabase.table("iot_devices").delete().eq("id", str(device_id)).eq("user_id", user_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị để xóa.")
    return None

@router.post("/test")
def test_iot_connection(
    req: IoTDeviceTestRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Test kết nối (Ping) thử tới địa chỉ IP LAN trước khi lưu vào CSDL."""
    try:
        d = tinytuya.OutletDevice(req.device_id, req.ip_address, req.local_key)
        d.set_version(req.version)
        d.set_socketPersistent(True) 
        
        status_data = d.status()
        
        if "Error" in status_data:
            return {"success": False, "message": f"Tín hiệu bị lỗi: {status_data}"}
            
        dps_data = status_data.get("dps", {})
        return {
            "success": True, 
            "message": "Kết nối IP LAN thành công!", 
            "dps": dps_data
        }
    except Exception as e:
        logger.error(f"Test connection error: {e}")
        return {"success": False, "message": f"Lỗi thực thi: {str(e)}"}
