import { useState, useEffect, useCallback } from "react";
import { CloudSun, MapPin, Droplets, Wind, RefreshCw } from "lucide-react";
import styles from "../ChatPage.module.css";
import api from "../../../services/api";
import { useAuthStore } from "../../../stores/authStore";

const CACHE_KEY = "jarvis_weather_cache";
const DEFAULT_TTL = 1800000; // 30 minutes in ms

interface WeatherData {
  answer?: string;
  temperature?: number;
  location?: string;
  humidity?: number;
  wind_speed?: number;
  icon?: string;
  description?: string;
  [key: string]: unknown;
}

interface CachedWeather {
  data: WeatherData;
  expire_time: number;
}

export default function WeatherWidget() {
  const { user, updatePreferences } = useAuthStore();
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [locating, setLocating] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [locationName, setLocationName] = useState("Trà Vinh");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const getCacheTtl = (): number => {
    try {
      const userStr = localStorage.getItem("user");
      if (userStr) {
        const user = JSON.parse(userStr);
        const ttl = user?.preferences?.weather_cache_ttl;
        if (ttl) return Number(ttl) * 1000; // convert seconds to ms
      }
    } catch {
      /* ignore */
    }
    return DEFAULT_TTL;
  };

  const getDefaultLocation = (): string => {
    try {
      const userStr = localStorage.getItem("user");
      if (userStr) {
        const user = JSON.parse(userStr);
        return user?.preferences?.default_location || "Trà Vinh";
      }
    } catch {
      /* ignore */
    }
    return "Trà Vinh";
  };

  const fetchWeather = useCallback(
    async (lat?: number, lon?: number) => {
      setLoading(true);
      try {
        // Check cache first
        const cached = localStorage.getItem(CACHE_KEY);
        if (cached && !refreshing) {
          // Skip cache if we are manually refreshing
          const parsed: CachedWeather = JSON.parse(cached);
          // Only use cache if it's not expired AND it has actual data
          if (
            Date.now() < parsed.expire_time &&
            parsed.data &&
            Object.keys(parsed.data).length > 0
          ) {
            setWeather(parsed.data);
            if (parsed.data.location) setLocationName(parsed.data.location);

            // Deduce the last updated time from cache creation time (expire_time - ttl)
            const ttl = getCacheTtl();
            setLastUpdated(new Date(parsed.expire_time - ttl));

            setLoading(false);
            setRefreshing(false);
            return;
          }
        }

        // Call backend API
        const params: Record<string, string> = {};
        if (lat !== undefined && lon !== undefined) {
          params.lat = String(lat);
          params.lon = String(lon);
        }

        const res = await api.get("/agent/weather", { params });
        const data = res.data as WeatherData;
        setWeather(data);
        setLastUpdated(new Date());

        // Try to extract location name from the answer
        let newLocationName = "";
        if (data.location) {
          newLocationName = data.location;
          setLocationName(data.location);
        } else {
          newLocationName = lat
            ? `${lat.toFixed(2)}, ${lon?.toFixed(2)}`
            : getDefaultLocation();
          setLocationName(newLocationName);
        }

        // If user fetched via GPS (lat/lon provided) and we got a location name, save it to DB
        if (lat !== undefined && lon !== undefined && newLocationName && user) {
          const currentPrefs = user.preferences || {};
          if (currentPrefs.default_location !== newLocationName) {
            updatePreferences({
              ...currentPrefs,
              default_location: newLocationName,
            }).catch((err) =>
              console.error("Failed to persist GPS location:", err),
            );
          }
        }

        // Save to cache with TTL
        const cacheEntry: CachedWeather = {
          data,
          expire_time: Date.now() + getCacheTtl(),
        };
        localStorage.setItem(CACHE_KEY, JSON.stringify(cacheEntry));
      } catch (err) {
        console.error("Failed to fetch weather:", err);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [user, updatePreferences, refreshing],
  );

  const handleManualRefresh = () => {
    setRefreshing(true);
    // Setting refreshing=true will cause fetchWeather to bypass cache
  };

  useEffect(() => {
    if (refreshing) {
      fetchWeather();
    }
  }, [refreshing, fetchWeather]);

  // Load on mount with default location (no geolocation auto-prompt)
  useEffect(() => {
    fetchWeather();
  }, [fetchWeather]);

  const handleUpdateLocation = () => {
    if (!navigator.geolocation) {
      console.warn("Geolocation not supported");
      return;
    }

    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        // Clear cache to force refetch
        localStorage.removeItem(CACHE_KEY);
        fetchWeather(position.coords.latitude, position.coords.longitude);
        setLocating(false);
      },
      (error) => {
        console.warn("Geolocation denied or failed:", error);
        setLocating(false);
        // Fetch with default location
        localStorage.removeItem(CACHE_KEY);
        fetchWeather();
      },
      { enableHighAccuracy: false, timeout: 10000 },
    );
  };

  // Parse answer text for display
  const getDisplayInfo = () => {
    if (!weather) return null;

    // OpenWeather API puts the actual structured data inside `weather.data`
    // which is an object keyed by location names (e.g. {"Trà Vinh Province": {...}, "Xã Đại Phước": {...}})
    let temp, humidity, wind, desc, icon;
    const answer = weather.answer || "";

    const dataObj = weather.data as Record<string, any>;
    if (dataObj && typeof dataObj === "object") {
      // Find the first location key that has actual weather data
      const locKey = Object.keys(dataObj).find(
        (key) => dataObj[key] && dataObj[key].temp !== undefined,
      );

      if (locKey) {
        const item = dataObj[locKey];
        // Convert Kelvin to Celsius if necessary, though it seems some are already Celsius.
        // 299 K is clearly Kelvin. Formula: C = K - 273.15
        if (item.temp > 200) {
          temp = Math.round(item.temp - 273.15);
        } else {
          temp = Math.round(item.temp);
        }

        humidity = item.humidity;
        wind = item.wind_speed;

        if (item.weather && item.weather.length > 0) {
          desc = item.weather[0].description;
          icon = item.weather[0].icon;
        }
      }
    }

    // Fallbacks if data parsing fails but we have them at root level (unlikely now)
    temp = temp !== undefined ? temp : weather.temperature;
    humidity = humidity !== undefined ? humidity : weather.humidity;
    wind = wind !== undefined ? wind : weather.wind_speed;
    desc = desc || weather.description || "";

    return { answer, temp, humidity, wind, desc, icon };
  };

  const info = getDisplayInfo();

  return (
    <div className={`${styles.widget} ${styles.weatherWidget} glass-panel`}>
      <div className={styles.widgetHeader}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <CloudSun size={16} className={styles.widgetIcon} />
          <h3 className={styles.widgetTitle}>Thời tiết</h3>
        </div>
        <div style={{ display: "flex", gap: "4px" }}>
          <button
            className={styles.weatherLocationBtn}
            onClick={handleManualRefresh}
            disabled={refreshing || locating}
            title="Làm mới dữ liệu"
          >
            <RefreshCw
              size={14}
              className={refreshing ? styles.spinning : ""}
            />
          </button>
          <button
            className={styles.weatherLocationBtn}
            onClick={handleUpdateLocation}
            disabled={locating || refreshing}
            title="Cập nhật vị trí hiện tại"
          >
            {locating ? (
              <RefreshCw size={14} className={styles.spinning} />
            ) : (
              <MapPin size={14} />
            )}
          </button>
        </div>
      </div>

      {loading ? (
        <div className={styles.weatherSkeleton}>
          <div className={styles.skeletonLine} style={{ width: "60%" }} />
          <div className={styles.skeletonLine} style={{ width: "80%" }} />
          <div className={styles.skeletonLine} style={{ width: "45%" }} />
        </div>
      ) : weather ? (
        <div className={styles.weatherBody}>
          <div className={styles.weatherLocation}>
            <MapPin size={12} />
            <span>{locationName}</span>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div>
              {info?.temp !== undefined && (
                <div className={styles.weatherTemp}>{info.temp}°C</div>
              )}
              {info?.desc && (
                <div className={styles.weatherDesc}>{info.desc}</div>
              )}
            </div>

            {info?.icon && (
              <img
                src={`https://openweathermap.org/img/wn/${info.icon}@2x.png`}
                alt="Thời tiết"
                style={{
                  width: "64px",
                  height: "64px",
                  filter:
                    "drop-shadow(0 4px 6px rgba(0,0,0,0.2)) drop-shadow(0 0 10px rgba(255,255,255,0.4))",
                  transform: "scale(1.2) translateY(-4px)",
                }}
              />
            )}
          </div>

          <div className={styles.weatherDetails}>
            {info?.humidity !== undefined && (
              <div className={styles.weatherDetailItem} title="Độ ẩm">
                <Droplets size={12} />
                <span>{info.humidity}%</span>
              </div>
            )}
            {info?.wind !== undefined && (
              <div className={styles.weatherDetailItem} title="Tốc độ gió">
                <Wind size={12} />
                <span>{info.wind} m/s</span>
              </div>
            )}
          </div>

          {info?.answer && info.temp === undefined && (
            <div className={styles.weatherAnswer}>{info.answer}</div>
          )}

          {lastUpdated && (
            <div
              style={{
                fontSize: "10px",
                color: "var(--text-muted)",
                marginTop: "4px",
                textAlign: "right",
              }}
            >
              Cập nhật lúc:{" "}
              {lastUpdated.toLocaleTimeString("vi-VN", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </div>
          )}
        </div>
      ) : (
        <div className={styles.weatherError}>
          Không thể tải dữ liệu thời tiết
        </div>
      )}
    </div>
  );
}
