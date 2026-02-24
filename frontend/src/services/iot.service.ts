import api from "./api";

export interface IoTDevice {
  id: string;
  user_id: string;
  name: string;
  ip_address: string;
  mac_address?: string;
  is_active: boolean;
  device_id: string;
  local_key: string;
  version: number;
  device_type: "single" | "multi";
  dps_mapping: Record<string, string>;
}

export type IoTDeviceCreate = Omit<IoTDevice, "id" | "user_id" | "is_active">;

export const iotService = {
  // ── Lấy danh sách thiết bị
  getDevices: async (): Promise<IoTDevice[]> => {
    const res = await api.get<IoTDevice[]>("/iot/devices");
    return res.data;
  },

  // ── Thêm thiết bị mới
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

  // ── Test Ping
  testConnection: async (data: {
    ip_address: string;
    device_id: string;
    local_key: string;
    version: number;
  }): Promise<{ success: boolean; message: string; dps?: any }> => {
    const res = await api.post("/iot/devices/test", data);
    return res.data;
  },
};
