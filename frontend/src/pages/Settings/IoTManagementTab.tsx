import { useState, useEffect, type FormEvent } from "react";
import { Plus, Trash, Wifi, X, Radar, Check, Info } from "lucide-react";
import {
  iotService,
  type IoTDevice,
  type IoTDeviceCreate,
} from "../../services/iot.service";
import styles from "./SettingsPage.module.css";

export default function IoTManagementTab() {
  const [devices, setDevices] = useState<IoTDevice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Guide State
  const [showGuide, setShowGuide] = useState(false);

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 6;

  // States Modal Add Device
  const [isAdding, setIsAdding] = useState(false);
  const [newDevice, setNewDevice] = useState<Partial<IoTDeviceCreate>>({
    device_type: "single",
    version: 3.4,
    dps_mapping: {},
  });

  // State Test
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  const [testing, setTesting] = useState(false);

  // States Scan Devices
  const [scanning, setScanning] = useState(false);
  const [scannedDevices, setScannedDevices] = useState<any[] | null>(null);

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      setLoading(true);
      const data = await iotService.getDevices();
      setDevices(data || []);
    } catch (err) {
      setError("Không thể load danh sách thiết bị");
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async () => {
    if (!newDevice.ip_address || !newDevice.device_id || !newDevice.local_key) {
      setTestResult({
        success: false,
        message: "Vui lòng nhập IP, Device ID và Local Key trước khi Test.",
      });
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const res = await iotService.testConnection({
        ip_address: newDevice.ip_address,
        device_id: newDevice.device_id,
        local_key: newDevice.local_key,
        version: newDevice.version || 3.4,
      });
      setTestResult(res);
      // Nếu là ổ đa năng và test thành công trả về dps, tự động map keys
      if (res.success && res.dps && newDevice.device_type === "multi") {
        const keys = Object.keys(res.dps);
        const initMapping: Record<string, string> = {};
        keys.forEach((k) => {
          // Lọc bỏ dps rác thường gặp
          if (
            ![
              "9",
              "10",
              "11",
              "12",
              "13",
              "14",
              "38",
              "40",
              "41",
              "42",
              "43",
              "44",
            ].includes(k)
          ) {
            initMapping[k] = `Cổng ${k}`;
          }
        });
        setNewDevice((prev) => ({ ...prev, dps_mapping: initMapping }));
      }
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || "Lỗi Network khi test.",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleScanLAN = async () => {
    setScanning(true);
    setScannedDevices(null);
    try {
      const res = await iotService.scanLocalDevices();
      if (res.success) {
        setScannedDevices(res.devices || []);
      } else {
        alert("Lỗi khi quét mạng LAN. Vui lòng thử lại!");
      }
    } catch (err) {
      alert("Lỗi Server Timeout khi dò tìm sóng.");
    } finally {
      setScanning(false);
    }
  };

  const handleApplyScannedDevice = (dev: any) => {
    setNewDevice((prev) => ({
      ...prev,
      ip_address: dev.ip,
      device_id: dev.device_id,
      version: dev.version ? parseFloat(dev.version) : 3.4,
    }));
    setScannedDevices(null); // Đóng hộp scan
  };

  const handleSaveDevice = async (e: FormEvent) => {
    e.preventDefault();
    if (
      !newDevice.name ||
      !newDevice.ip_address ||
      !newDevice.device_id ||
      !newDevice.local_key
    )
      return;

    try {
      await iotService.createDevice(newDevice as IoTDeviceCreate);
      setIsAdding(false);
      setNewDevice({ device_type: "single", version: 3.4, dps_mapping: {} });
      setTestResult(null);
      fetchDevices();
    } catch (err) {
      setTestResult({ success: false, message: "Lỗi lưu DB thiết bị." });
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Bạn có chắc chắn muốn xóa thiết bị này khỏi hệ thống?"))
      return;
    try {
      await iotService.deleteDevice(id);
      fetchDevices();
    } catch (err) {
      alert("Lỗi xoá thiết bị!");
    }
  };

  if (loading) return <div>Đang tải danh sách thiết bị...</div>;

  return (
    <div style={{ marginTop: "1rem" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
        }}
      >
        <h2
          className={styles.pageTitle}
          style={{
            margin: 0,
            display: "flex",
            alignItems: "center",
            gap: "12px",
          }}
        >
          Quản lý Smart Home
          <button
            onClick={() => setShowGuide(!showGuide)}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              display: "flex",
              padding: "4px",
              borderRadius: "50%",
              transition: "all 0.2s",
            }}
            title="Hướng dẫn lấy thông số Tuya"
          >
            <Info size={18} />
          </button>
        </h2>
        <button
          className={styles.saveBtn}
          style={{ padding: "8px 16px", margin: 0, width: "auto" }}
          onClick={() => setIsAdding(true)}
        >
          <Plus size={16} /> Thêm thiết bị mới
        </button>
      </div>

      {showGuide && (
        <div
          style={{
            marginBottom: "20px",
            background: "rgba(59, 130, 246, 0.1)",
            border: "1px solid rgba(59, 130, 246, 0.3)",
            borderRadius: "8px",
            padding: "16px",
            position: "relative",
          }}
        >
          <button
            onClick={() => setShowGuide(false)}
            style={{
              position: "absolute",
              top: "12px",
              right: "12px",
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
            }}
          >
            <X size={16} />
          </button>
          <h4
            style={{
              margin: "0 0 12px 0",
              color: "var(--blue-500)",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <Info size={18} /> Hướng dẫn lấy thông số Tuya
          </h4>
          <ol
            style={{
              margin: 0,
              paddingLeft: "20px",
              fontSize: "14px",
              color: "var(--text-primary)",
              lineHeight: "1.6",
            }}
          >
            <li>
              Tải app SmartLife/Tuya, kết nối các ổ cắm vào cùng chung mạng WiFi
              với máy chủ này.
            </li>
            <li>
              Đăng ký tài khoản Developer trên{" "}
              <a
                href="https://iot.tuya.com/"
                target="_blank"
                rel="noreferrer"
                style={{ color: "var(--blue-500)" }}
              >
                iot.tuya.com
              </a>
              , tạo 1 Cloud Project và liên kết App SmartLife vào Project đó.
            </li>
            <li>
              Tại máy tính, mở Terminal và chạy lệnh:{" "}
              <code
                style={{
                  background: "var(--bg-primary)",
                  padding: "2px 6px",
                  borderRadius: "4px",
                }}
              >
                python -m tinytuya wizard
              </code>
              . Nhập <strong>Access ID/Client ID</strong> (vào ô API Key) và{" "}
              <strong>Access Secret/Client Secret</strong> (vào ô API Secret)
              khi được hỏi.
            </li>
            <li>
              Wizard sẽ quét toàn bộ thiết bị và tải xuống file{" "}
              <code
                style={{
                  background: "var(--bg-primary)",
                  padding: "2px 6px",
                  borderRadius: "4px",
                }}
              >
                devices.json
              </code>
              . Mở file này ra để lấy chính xác <strong>Device ID</strong> và{" "}
              <strong>Local Key</strong> của từng thiết bị.
            </li>
          </ol>
          <div
            style={{
              marginTop: "12px",
              fontSize: "13px",
              color: "var(--text-muted)",
              fontStyle: "italic",
            }}
          >
            Mẹo: Bạn không cần nhập tay IP. Hãy bấm{" "}
            <strong>Thêm thiết bị mới -&gt; Quét Radar Tự Động</strong> để quét
            IP cục bộ nhanh nhất.
          </div>
        </div>
      )}

      {error && <div className={styles.error}>{error}</div>}

      {isAdding && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h3 className={styles.modalTitle}>
                <Wifi size={20} /> Khai báo ổ cắm Tuya LAN
              </h3>
              <div
                style={{ display: "flex", gap: "12px", alignItems: "center" }}
              >
                <button
                  type="button"
                  onClick={handleScanLAN}
                  disabled={scanning}
                  style={{
                    background: scanning
                      ? "transparent"
                      : "rgba(16, 185, 129, 0.1)",
                    color: scanning ? "var(--text-muted)" : "#10b981",
                    border: "1px solid currentColor",
                    padding: "6px 12px",
                    borderRadius: "16px",
                    fontSize: "13px",
                    display: "flex",
                    gap: "6px",
                    alignItems: "center",
                    cursor: scanning ? "wait" : "pointer",
                  }}
                >
                  <Radar
                    size={14}
                    className={scanning ? styles.spinAnimation : ""}
                  />{" "}
                  {scanning ? "Đang dò sóng UDP..." : "Quét Radar Tự Động"}
                </button>
                <button
                  className={styles.closeButton}
                  onClick={() => setIsAdding(false)}
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            {scannedDevices !== null && (
              <div
                style={{
                  marginBottom: "20px",
                  background: "var(--bg-secondary)",
                  borderRadius: "8px",
                  padding: "16px",
                  border: "1px dashed #10b981",
                }}
              >
                <div
                  style={{
                    fontWeight: 600,
                    marginBottom: "12px",
                    color: "#10b981",
                    display: "flex",
                    gap: "8px",
                    alignItems: "center",
                  }}
                >
                  <Radar size={16} /> Radar tìm thấy ({scannedDevices.length})
                  thiết bị qua sóng WiFi LAN:
                </div>
                {scannedDevices.length === 0 ? (
                  <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                    Không tìm thấy ổ cắm Tuya nào đang cắm điện cùng mạng WiFi
                    với Server.
                  </div>
                ) : (
                  <div style={{ display: "grid", gap: "8px" }}>
                    {scannedDevices.map((dev, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          background: "var(--bg-primary)",
                          padding: "12px",
                          borderRadius: "6px",
                          border: "1px solid var(--border-light)",
                        }}
                      >
                        <div>
                          <div
                            style={{
                              fontWeight: 500,
                              display: "flex",
                              gap: "8px",
                              alignItems: "center",
                              color: "var(--text-primary)",
                            }}
                          >
                            <Wifi size={14} color="var(--primary)" /> IP:{" "}
                            {dev.ip}
                          </div>
                          <div
                            style={{
                              fontSize: "12px",
                              color: "var(--text-muted)",
                              marginTop: "4px",
                            }}
                          >
                            ID: {dev.device_id} • v{dev.version}
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleApplyScannedDevice(dev)}
                          style={{
                            background: "#10b981",
                            color: "white",
                            border: "none",
                            padding: "6px 12px",
                            borderRadius: "6px",
                            cursor: "pointer",
                            display: "flex",
                            gap: "4px",
                            fontSize: "13px",
                            fontWeight: 500,
                          }}
                        >
                          <Check size={14} /> Điền vào form
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => setScannedDevices(null)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    fontSize: "13px",
                    marginTop: "12px",
                    cursor: "pointer",
                    textDecoration: "underline",
                    width: "100%",
                    textAlign: "center",
                  }}
                >
                  Đóng hộp tìm kiếm
                </button>
              </div>
            )}

            <form onSubmit={handleSaveDevice}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "16px",
                  marginBottom: "16px",
                }}
              >
                <div className={styles.field}>
                  <label>Tên định danh (VD: Ổ cắm phòng ngủ)</label>
                  <input
                    required
                    value={newDevice.name || ""}
                    onChange={(e) =>
                      setNewDevice({ ...newDevice, name: e.target.value })
                    }
                  />
                </div>
                <div className={styles.field}>
                  <label>Địa chỉ IP LAN</label>
                  <input
                    required
                    placeholder="192.168.1.x"
                    value={newDevice.ip_address || ""}
                    onChange={(e) =>
                      setNewDevice({ ...newDevice, ip_address: e.target.value })
                    }
                  />
                </div>
                <div className={styles.field}>
                  <label>Device ID</label>
                  <input
                    required
                    value={newDevice.device_id || ""}
                    onChange={(e) =>
                      setNewDevice({ ...newDevice, device_id: e.target.value })
                    }
                  />
                </div>
                <div className={styles.field}>
                  <label>Local Key</label>
                  <input
                    required
                    value={newDevice.local_key || ""}
                    onChange={(e) =>
                      setNewDevice({ ...newDevice, local_key: e.target.value })
                    }
                  />
                </div>
                <div className={styles.field}>
                  <label>Protocol Version</label>
                  <select
                    value={newDevice.version}
                    onChange={(e) =>
                      setNewDevice({
                        ...newDevice,
                        version: parseFloat(e.target.value),
                      })
                    }
                  >
                    <option value={3.1}>3.1</option>
                    <option value={3.3}>3.3</option>
                    <option value={3.4}>3.4</option>
                    <option value={3.5}>3.5</option>
                  </select>
                </div>
                <div className={styles.field}>
                  <label>Loại ổ cắm</label>
                  <select
                    value={newDevice.device_type}
                    onChange={(e) =>
                      setNewDevice({
                        ...newDevice,
                        device_type: e.target.value as any,
                      })
                    }
                  >
                    <option value="single">Single (1 Công tắc)</option>
                    <option value="multi">Multi (Đa công tắc / Ổ chia)</option>
                  </select>
                </div>
              </div>

              {testResult && (
                <div
                  className={testResult.success ? styles.success : styles.error}
                  style={{ marginBottom: "16px" }}
                >
                  {testResult.success
                    ? `✅ ${testResult.message}`
                    : `❌ ${testResult.message}`}
                </div>
              )}

              {newDevice.device_type === "multi" && (
                <div
                  style={{
                    marginBottom: "16px",
                    padding: "12px",
                    background: "var(--bg-secondary)",
                    borderRadius: "8px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "8px",
                    }}
                  >
                    <div style={{ fontWeight: 500 }}>
                      Cấu hình Tên Cổng (DPS Mapping):
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        const currentKeys = Object.keys(
                          newDevice.dps_mapping || {},
                        );
                        let nextPort = 1;
                        while (currentKeys.includes(nextPort.toString()))
                          nextPort++;
                        setNewDevice((prev) => ({
                          ...prev,
                          dps_mapping: {
                            ...prev.dps_mapping,
                            [nextPort]: `Cổng ${nextPort}`,
                          } as any,
                        }));
                      }}
                      style={{
                        background: "var(--primary)",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        padding: "4px 8px",
                        fontSize: "12px",
                        cursor: "pointer",
                      }}
                    >
                      + Thêm cổng
                    </button>
                  </div>

                  {!newDevice.dps_mapping ||
                  Object.keys(newDevice.dps_mapping).length === 0 ? (
                    <div
                      style={{
                        fontSize: "13px",
                        color: "var(--text-muted)",
                        fontStyle: "italic",
                        marginBottom: "8px",
                      }}
                    >
                      Chưa có cổng nào. Hãy ấn Test Kết Nối để tự động lấy, hoặc
                      tự Thêm Cổng.
                    </div>
                  ) : (
                    Object.keys(newDevice.dps_mapping).map((dps) => (
                      <div
                        key={dps}
                        style={{
                          display: "flex",
                          gap: "8px",
                          marginBottom: "8px",
                          alignItems: "center",
                        }}
                      >
                        <span style={{ width: "80px" }}>Cổng {dps}</span>
                        <input
                          style={{
                            padding: "6px",
                            flex: 1,
                            borderRadius: "4px",
                            border: "1px solid var(--border-light)",
                          }}
                          value={newDevice.dps_mapping![dps]}
                          onChange={(e) => {
                            setNewDevice((prev) => ({
                              ...prev,
                              dps_mapping: {
                                ...prev.dps_mapping,
                                [dps]: e.target.value,
                              } as any,
                            }));
                          }}
                          placeholder="VD: Quạt trần"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const newMap = { ...newDevice.dps_mapping };
                            delete newMap[dps];
                            setNewDevice((prev) => ({
                              ...prev,
                              dps_mapping: newMap,
                            }));
                          }}
                          style={{
                            background: "transparent",
                            color: "var(--error)",
                            border: "none",
                            cursor: "pointer",
                            padding: "4px",
                          }}
                        >
                          <Trash size={16} />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}

              <div
                style={{
                  display: "flex",
                  gap: "12px",
                  justifyContent: "flex-end",
                }}
              >
                <button
                  type="button"
                  className={styles.logoutBtn}
                  style={{
                    borderRadius: "8px",
                    border: "1px solid currentColor",
                  }}
                  onClick={handleTestConnection}
                  disabled={testing}
                >
                  {testing ? "Đang Ping LAN..." : "Test Kết Nối (Ping)"}
                </button>
                <button
                  type="submit"
                  className={styles.saveBtn}
                  style={{ margin: 0, width: "140px" }}
                  disabled={!testResult?.success}
                  title={
                    !testResult?.success
                      ? "Chỉ được lưu sau khi Test kết nối LAN thành công"
                      : ""
                  }
                >
                  Lưu Thiết Bị
                </button>
              </div>

              {!testResult?.success && (
                <div
                  style={{
                    textAlign: "right",
                    fontSize: "12px",
                    color: "var(--text-muted)",
                    marginTop: "8px",
                  }}
                >
                  *Bắt buộc phải Test Ping thành công trước khi Lưu
                </div>
              )}
            </form>
          </div>
        </div>
      )}

      {/* List Devices */}
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}
      >
        {devices
          .slice(
            (currentPage - 1) * ITEMS_PER_PAGE,
            currentPage * ITEMS_PER_PAGE,
          )
          .map((dev) => (
            <div
              key={dev.id}
              className={styles.card}
              style={{ height: "100%", position: "relative" }}
            >
              <button
                onClick={() => handleDelete(dev.id)}
                style={{
                  position: "absolute",
                  top: "16px",
                  right: "16px",
                  background: "transparent",
                  border: "none",
                  color: "var(--error)",
                  cursor: "pointer",
                }}
              >
                <Trash size={16} />
              </button>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  marginBottom: "16px",
                }}
              >
                <div
                  style={{
                    background: dev.is_active
                      ? "rgba(16, 185, 129, 0.1)"
                      : "rgba(239, 68, 68, 0.1)",
                    color: dev.is_active ? "#10b981" : "#ef4444",
                    padding: "12px",
                    borderRadius: "50%",
                  }}
                >
                  <Wifi size={24} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: "16px" }}>{dev.name}</h3>
                  <span
                    style={{ fontSize: "12px", color: "var(--text-muted)" }}
                  >
                    IP: {dev.ip_address} • v{dev.version}
                  </span>
                </div>
              </div>

              <div
                style={{
                  fontSize: "13px",
                  color: "var(--text-secondary)",
                  background: "var(--bg-secondary)",
                  padding: "12px",
                  borderRadius: "8px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "4px",
                  }}
                >
                  <span>
                    Loại:{" "}
                    <b>
                      {dev.device_type === "single" ? "Ổ cắm đơn" : "Ổ đa năng"}
                    </b>
                  </span>
                  <span>ID: {dev.device_id.substring(0, 6)}...</span>
                </div>

                {dev.device_type === "multi" &&
                  dev.dps_mapping &&
                  Object.keys(dev.dps_mapping).length > 0 && (
                    <div
                      style={{
                        marginTop: "12px",
                        borderTop: "1px solid var(--border-light)",
                        paddingTop: "8px",
                      }}
                    >
                      <div style={{ fontWeight: 500, marginBottom: "4px" }}>
                        Ports (DPS):
                      </div>
                      <div
                        style={{
                          display: "flex",
                          flexWrap: "wrap",
                          gap: "8px",
                        }}
                      >
                        {Object.values(dev.dps_mapping).map(
                          (label: any, idx) => (
                            <span
                              key={idx}
                              style={{
                                background: "rgba(0,0,0,0.05)",
                                padding: "2px 8px",
                                borderRadius: "12px",
                                border: "1px solid rgba(0,0,0,0.1)",
                              }}
                            >
                              {label}
                            </span>
                          ),
                        )}
                      </div>
                    </div>
                  )}
              </div>
            </div>
          ))}
        {devices.length === 0 && !isAdding && (
          <div
            style={{
              gridColumn: "1 / -1",
              textAlign: "center",
              padding: "40px",
              color: "var(--text-muted)",
              border: "1px dashed var(--border-light)",
              borderRadius: "12px",
            }}
          >
            Không có thiết bị IoT nào được quản lý. Ấn Thêm Thiết Bị để bắt đầu.
          </div>
        )}
      </div>

      {/* Pagination Controls */}
      {devices.length > ITEMS_PER_PAGE && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: "16px",
            marginTop: "24px",
            paddingTop: "16px",
            borderTop: "1px solid var(--border-light)",
          }}
        >
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-light)",
              padding: "6px 12px",
              borderRadius: "6px",
              cursor: currentPage === 1 ? "not-allowed" : "pointer",
              opacity: currentPage === 1 ? 0.5 : 1,
              color: "var(--text-primary)",
            }}
          >
            Trang trước
          </button>
          <span style={{ fontSize: "14px", color: "var(--text-muted)" }}>
            Trang {currentPage} / {Math.ceil(devices.length / ITEMS_PER_PAGE)}
          </span>
          <button
            onClick={() =>
              setCurrentPage((p) =>
                Math.min(Math.ceil(devices.length / ITEMS_PER_PAGE), p + 1),
              )
            }
            disabled={
              currentPage === Math.ceil(devices.length / ITEMS_PER_PAGE)
            }
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-light)",
              padding: "6px 12px",
              borderRadius: "6px",
              cursor:
                currentPage === Math.ceil(devices.length / ITEMS_PER_PAGE)
                  ? "not-allowed"
                  : "pointer",
              opacity:
                currentPage === Math.ceil(devices.length / ITEMS_PER_PAGE)
                  ? 0.5
                  : 1,
              color: "var(--text-primary)",
            }}
          >
            Trang sau
          </button>
        </div>
      )}
    </div>
  );
}
