import logging
import tinytuya
from typing import Optional
from langchain_core.tools import tool

from app.core.database import get_supabase_admin_client

logger = logging.getLogger(__name__)

@tool
def list_smart_home_devices(user_id: str = "") -> str:
    """
    [STEP 1] KHÁM PHÁ THIẾT BỊ: Lấy danh sách tất cả các ổ cắm/thiết bị Smart Home của người dùng.
    Dùng công cụ này TRƯỚC TIÊN để tìm chính xác `device_id` và `dps_index` của thiết bị mà người dùng muốn điều khiển.
    
    Args:
        user_id (str): Nội bộ tự có, bỏ qua.
        
    Returns:
        JSON string chứa danh sách tên, id, tình trạng online và cấu hình cổng (dps_mapping) của tất cả thiết bị.
    """
    if not user_id:
        return "Lỗi nội bộ Agent: Thiếu user_id để xác thực CSDL."
        
    supabase = get_supabase_admin_client()
    res = supabase.table("iot_devices").select("*").eq("user_id", user_id).execute()
    devices = res.data
    
    if not devices:
        return "Người dùng chưa cấu hình thiết bị nhà thông minh nào. Hãy gợi ý họ vào Cài đặt -> Nhà thông minh để thêm."
        
    output = []
    for d in devices:
        output.append({
            "name": d.get("name"),
            "device_id": d.get("device_id"),
            "device_type": d.get("device_type"),
            "is_active": d.get("is_active"),
            "dps_mapping": d.get("dps_mapping", {"1": "Default Switch"}) if d.get("device_type") == "multi" else {"1": "Công tắc chính"}
        })
    import json
    return json.dumps(output, ensure_ascii=False)


def _auto_heal_ip(device: dict) -> str:
    """Tự quét mạng LAN tìm IP mới dựa trên ID/MAC nếu IP cũ bị timeout."""
    logger.warning(f"🔄 Đang càn quét UDP mạng LAN để tìm IP mới cho thiết bị {device.get('name')}...")
    try:
        # Scan LAN trong 5 giây (nhanh)
        devices_found = tinytuya.deviceScan(False, 5) 
        for ip, dev_info in devices_found.items():
            if dev_info.get("id") == device.get("device_id"):
                new_ip = dev_info.get("ip")
                if new_ip:
                    # Update lại IP mới vào DB
                    supabase = get_supabase_admin_client()
                    supabase.table("iot_devices").update({"ip_address": new_ip, "is_active": True}).eq("id", device["id"]).execute()
                    return new_ip
    except Exception as e:
        logger.error(f"Lỗi scan IP: {e}")
    
    # Nếu vẫn không thấy, chốt đơn Offline
    try:
        supabase = get_supabase_admin_client()
        supabase.table("iot_devices").update({"is_active": False}).eq("id", device["id"]).execute()
    except:
        pass
    return ""

def _execute_tuya_command(device: dict, dps_target: str, action: str) -> str:
    """Thực thi lệnh Turn On/Off/Status. Cơ chế Fallback Self-Healing IP LAN."""
    d = tinytuya.OutletDevice(device["device_id"], device["ip_address"], device["local_key"])
    d.set_version(float(device.get("version", 3.3)))
    d.set_socketPersistent(True) # Keep-alive
    
    def try_action(dev_instance, dps):
        if action == "status":
            st = dev_instance.status()
            if "Error" in st: return None
            # Do thiết bị trả về list trạng thái dps, lấy đúng cổng
            val = st.get("dps", {}).get(str(dps))
            return {"status": "success", "is_on": val, "raw": st}
        elif action == "on":
            res = dev_instance.set_status(True, dps)
            if isinstance(res, dict) and "Error" in res: return None
            return {"status": "success", "msg": "Bật thành công"}
        elif action == "off":
            res = dev_instance.set_status(False, dps)
            if isinstance(res, dict) and "Error" in res: return None
            return {"status": "success", "msg": "Tắt thành công"}
            
    # ------ Lần 1: Cố gắng đánh vào IP cũ đang lưu ------
    res = try_action(d, dps_target)
    if res:
        if action == "status":
            state_text = 'BẬT 🟢' if res.get('is_on') else 'TẮT 🔴'
            return f"Kết nối ổn định. Trạng thái ổ '{device['name']}' (cổng dps_{dps_target}) đang {state_text}"
        return f"✅ Tác vụ '{action}' thành công trên cổng số {dps_target} của '{device['name']}'!"
        
    # ------ Lần 2: Mất kết nối, kích hoạt Auto Healing ------
    new_ip = _auto_heal_ip(device)
    if not new_ip:
        return f"❌ Thiết bị '{device['name']}' mất phản hồi mạng LAN. Khả năng cao đã đổi Wifi hoặc bị rút phích cắm!"
        
    # Thử lại cùng IP mới lấy
    d.address = new_ip
    res = try_action(d, dps_target)
    if res:
        if action == "status":
            state_text = 'BẬT 🟢' if res.get('is_on') else 'TẮT 🔴'
            return f"🔄 KIẾN TRÚC IP HEALING KÍCH HOẠT: Tìm thấy IP mới ({new_ip}). Trạng thái cổng {dps_target} là {state_text}"
        return f"🔄 KIẾN TRÚC IP HEALING KÍCH HOẠT: Đã túm được IP mới ({new_ip}) và thực thi '{action}' trên lỗ số {dps_target} thành công!"
    
    return f"⚠️ Túm được IP mới ({new_ip}) nhưng ruột thiết bị đang từ chối lệnh. Có thể do lỗi Firmware Tuya."


@tool
def toggle_smart_plug(device_id: str, action: str, dps_index: str = "1", user_id: str = "") -> str:
    """
    [STEP 2] THỰC THI THAO TÁC: Sử dụng để Bật/Tắt ổ cắm Smart Home.
    BẮT BUỘC phải dùng `list_smart_home_devices` trước để lấy id chuẩn xác.
    
    Args:
        device_id (str): ID của thiết bị (lấy từ list_smart_home_devices).
        action (str): Hành động. Chỉ nhận chữ: "on", "off" hoặc "status".
        dps_index (str): Số index của cổng cắm (VD: "1", "2"). NẾU LÀ Ổ ĐƠN THÌ MẶC ĐỊNH LÀ "1".
        user_id (str): ID được inject tự động.
    """
    if not user_id:
        return "Lỗi nội bộ Agent: Thiếu user_id để xác thực CSDL."
        
    action = action.lower()
    if action not in ["on", "off", "status"]:
        return f"Lỗi: Action '{action}' sai. Chỉ hỗ trợ 'on', 'off', 'status'."
        
    supabase = get_supabase_admin_client()
    res = supabase.table("iot_devices").select("*").eq("device_id", device_id).eq("user_id", user_id).execute()
    
    if not res.data:
        return f"Không tìm thấy dữ liệu cấu hình cho Device ID '{device_id}'. Hãy chắc chắn bạn lấy ID từ tool list_smart_home_devices."
        
    dev = res.data[0]
    return _execute_tuya_command(dev, str(dps_index), action)
