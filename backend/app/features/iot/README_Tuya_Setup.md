# Hướng dẫn Thiết lập và Sử dụng Module IoT Tuya Local (FastAPI + React)

Module IoT này được xây dựng theo kiến trúc **Local Network (LAN)** giúp Đại lý AI (Agent) điều khiển trực tiếp các ổ cắm thông minh Tuya/SmartLife mà không phải đi qua Cloud của hãng nhờ thư viện `tinytuya`. Tốc độ phản hồi cực nhanh (dưới 50ms) và tính bảo mật cao.

## 1. Yêu cầu Hệ thống

- Các thiết bị Tuya (`Smart Plug`, `Smart Switch`, `Power Strip`) đã được kết nối vào **cùng một mạng WiFi** với máy chủ chạy Backend (FastAPI).
- Đã cài đặt thư viện `tinytuya`. (Đã có sẵn trong `requirements.txt`).

---

## 2. Cách lấy thông số thiết bị Tuya (Device ID & Local Key)

Khác với điều khiển qua Cloud, điều khiển qua LAN bắt buộc phải có `Device ID` và `Local Key` (mật khẩu nội bộ) của từng thiết bị.

### Cách 1: Sử dụng Công cụ TuyAPI / Tinytuya Wizard (Khuyên dùng)

1. Tạo một tài khoản nhà phát triển trên trang [Tuya IoT Platform](https://iot.tuya.com/).
2. Tạo một Cloud Project, liên kết App SmartLife/Tuya trên điện thoại của bạn với Project đó.
3. Chạy lệnh wizard của `tinytuya` trên Terminal máy tính:
   ```bash
   python -m tinytuya wizard
   ```
4. Điền `Access ID/Client ID` (vào ô API Key), `Access Secret/Client Secret` (vào ô API Secret), `Device ID` (có thể xem trong phần Device Information trên app điện thoại).
5. Wizard sẽ tải xuống toàn bộ `Local Key` của tất cả các thiết bị trong nhà bạn và lưu thành file `devices.json`. Bạn mở file này ra lấy `id` và `key` tương ứng.
   _Ví dụ cấu trúc file trả về:_
   ```json
   [
     {
       "name": "Ổ cắm Ralli OC.09",
       "id": "a360xxxxxxxxxxxxna",
       "key": "Z$Nkxxxxxxx$Yt",
       "mac": "c4:82:ex:xx:xx:xx"
     }
   ]
   ```

### Cách 2: Sử dụng Auto-Discovery (Đã tích hợp trên Web)

Nếu bạn đã biết `Local Key` (từ Cách 1) nhưng ngại tìm IP và ID:

1. Mở trang Cài đặt -> **Quản lý Smart Home** trên giao diện Web.
2. Bấm **Thêm thiết bị mới** -> Chọn tính năng **📡 Quét Radar Tự Động**.
3. Hệ thống sẽ bắn gói tin `UDP Broadcast` ra toàn mạng LAN rà quét và tự động tóm cổ toàn bộ IP, ID của thiết bị Tuya đang cắm điện cùng mạng Wifi.
4. Bấm "Điền vào Form", sau đó bạn chỉ việc dán `Local Key` vào và ấn "Test Kết Nối (Ping)" là xong.

---

## 3. Cấu hình Cổng (Cho Ổ Đa Năng / Multi-Plug)

Có 2 loại thiết bị chính:

- **Ổ cắm Đơn (Single)**: Công tắc duy nhất thường nằm ở Port index `1`.
- **Ổ Đa năng (Multi)**: Chẳng hạn ổ nối dài có 3 khe cắm, 3 khe USB. Mỗi nút bật sẽ ứng với các Port (hay còn gọi là `DPS`) khác nhau. Thường giao động từ 1 -> 8.

**Luồng Setup Ổ Đa Năng trên Web:**

1. Khai báo thiết bị, chọn loại là **Multi (Đa công tắc / Ổ chia)**.
2. Nhấn nút **[Test Kết Nối (Ping)]**. Nếu thành công, Backend sẽ tự động trả về toàn bộ danh sách các Cổng DPS khả dụng hiện tại trên thiết bị (VD: tự dò ra Cổng 1, Cổng 2, Cổng 3, Cổng 7...).
3. Bảng "Cấu hình Tên Cổng (DPS Mapping)" sẽ tự động hiện ra. Bạn hãy sửa đổi các "Cổng X" thành tên thiết bị đang cắm cho dễ gọi (VD: Cổng 1 -> Quạt trần, Cổng 2 -> Đèn học).
4. Lưu thiết bị. Từ lúc này trở đi, Agent AI khi gọi lệnh sẽ biết tên các đèn để bật tắt chính xác cổng được yêu cầu.

---

## 4. Cách Agent tiếp cận Module IoT.

Agent hoạt động theo mô hình 2 bước (Discover & Execute):

1. **Bước 1 (Tool `list_smart_home_devices`)**: Khi User đưa ra Prompt như _"Bật quạt trần cho tôi"_. Agent trước hết phải gọi Tool này để tải list toàn bộ thiết bị đang quản lý từ Database ra context LLM. Agent sẽ đọc khối `dps_mapping` để nhận ra _"À, Quạt trần nằm ở Cổng số 1 trên thiết bị có ID XYZ"_.
2. **Bước 2 (Tool `toggle_smart_plug`)**: Agent tự động truyền `device_id="XYZ"`, `action="on"` và `dps_index="1"` vào Tool số 2 này. Code sẽ dùng thông số đó để kết nối thẳng `tinytuya.OutletDevice` để truyền tín hiệu Switch ON qua Wifi.

### 5. Cơ chế Auto-Heal (Tự sửa chữa IP lỗi)

Nhược điểm của ổ cắm Tuya Wifi là đôi khi IP Router cấp phát DHCP sẽ bị thay đổi ngẫu nhiên.
Module này đã thiết kế sẵn hàm `_auto_heal_ip()` tàng hình bên dưới.
Nếu Agent gọi lệnh vào IP A bị thất bại (Ping timeout), hệ thống lập tức xả sóng UDP vào LAN để càn quét lại thiết bị theo Device ID để update IP mới tinh `192.x.x.x` và lưu ngược vào Database Supabase. Do đó, người dùng không bao giờ cần phải lo cập nhật IP Lan bằng tay nữa!
