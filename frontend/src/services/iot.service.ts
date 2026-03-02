import api from "./api";

export interface IoTDevice {
  id: string;
  user_id: string;
  name: string;
  provider: "tuya" | "ezviz";
  ip_address?: string;
  mac_address?: string;
  is_active: boolean;
  device_id?: string;
  local_key?: string;
  version?: number;
  device_type: "single" | "multi" | "camera";
  dps_mapping?: Record<string, string>;
  config_data?: Record<string, any>;
}

export type IoTDeviceCreate = Omit<IoTDevice, "id" | "user_id" | "is_active">;

export const iotService = {
  // ── Lấy danh sách thiết bị (tất cả provider)
  getDevices: async (): Promise<IoTDevice[]> => {
    const res = await api.get<IoTDevice[]>("/iot/devices");
    return res.data;
  },

  // ── Thêm thiết bị mới (bao gồm cả Tuya lẫn EZVIZ)
  createDevice: async (data: IoTDeviceCreate): Promise<IoTDevice> => {
    const res = await api.post<IoTDevice>("/iot/devices", data);
    return res.data;
  },

  // ── Tự động dò Thiết bị Tuya Local
  scanLocalDevices: async (): Promise<{
    success: boolean;
    count: number;
    devices: any[];
  }> => {
    const res = await api.get("/iot/devices/scan?timeout=5");
    return res.data;
  },

  // ── Sửa thiết bị
  updateDevice: async (
    id: string,
    data: Partial<IoTDeviceCreate>,
  ): Promise<IoTDevice> => {
    const res = await api.patch<IoTDevice>(`/iot/devices/${id}`, data);
    return res.data;
  },

  // ── Xoá thiết bị
  deleteDevice: async (id: string): Promise<void> => {
    await api.delete(`/iot/devices/${id}`);
  },

  // ── Test Ping (Tuya only)
  testConnection: async (data: {
    ip_address: string;
    device_id: string;
    local_key: string;
    version: number;
  }): Promise<{ success: boolean; message: string; dps?: any }> => {
    const res = await api.post("/iot/devices/test", data);
    return res.data;
  },

  // ── Test kết nối EZVIZ Cloud
  testEzvizConnection: async (data: {
    username: string;
    password: string;
    region?: string;
  }): Promise<{ success: boolean; message: string; cameras?: any[] }> => {
    const res = await api.post("/iot/devices/test-ezviz", data);
    return res.data;
  },
};
