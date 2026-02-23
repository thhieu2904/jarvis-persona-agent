"""
Agent tool: Weather API.
Calls OpenWeather AI Assistant API to get a natural language weather report.
Includes cachetools for performance and API rate limit protection.
"""

import json
import urllib.request
import ssl
from langchain_core.tools import tool
from cachetools import TTLCache, cached
from app.config import get_settings

# Cache up to 100 different location queries for 30 minutes (1800 seconds) by default
weather_cache = TTLCache(maxsize=100, ttl=1800)


@cached(cache=weather_cache)
def _fetch_weather_from_api(location: str) -> str:
    settings = get_settings()
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        return "Lỗi: Chưa cấu hình OPENWEATHER_API_KEY trong hệ thống."

    url = "https://api.openweathermap.org/assistant/session"
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key
    }
    
    # Prompt the weather assistant explicitly
    prompt = f"Thời tiết hiện tại ở {location} thế nào?"
    data = json.dumps({"prompt": prompt}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        # Ignore SSL cert verification just in case (as seen in Windows dev env issues)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            res_data = response.read()
            json_res = json.loads(res_data)
            return json_res.get("answer", "Không lấy được thông tin thời tiết lúc này.")
    except Exception as e:
        return f"Lỗi khi tra cứu thời tiết: {str(e)}"


@tool
def get_weather(location: str) -> str:
    """Tra cứu thông tin thời tiết hiện tại cho một địa điểm (thành phố, tỉnh, quốc gia).
    
    BẮT BUỘC dùng tool này khi người dùng hỏi về thời tiết. TUYỆT ĐỐI KHÔNG DÙNG `search_web` để tìm thời tiết.
    Lưu ý:
    - Nếu người dùng KHÔNG chỉ định rõ định điểm (VD: "thời tiết hôm nay thế nào?"), hãy ưu tiên sử dụng nơi chốn hiện tại của người dùng (user_location) được cung cấp trong System Prompt.
    - Truyền vào tên địa phương (VD: "Càng Long, Trà Vinh", "Hà Nội").
    
    Args:
        location: Địa điểm cần tra cứu thời tiết.
        
    Returns:
        Câu trả lời tóm tắt về thời tiết từ hệ thống.
    """
    return _fetch_weather_from_api(location)


weather_tools = [get_weather]
