"""
Zalo Formatter & Sticker mapping.

Đọc cấu hình JSON để map thẻ cảm xúc với ID Sticker.
"""

import os
import json
from enum import Enum
from typing import Optional

# Đường dẫn tới file stickers.json (nằm cùng thư mục core)
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "stickers.json")

def load_stickers() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"NONE": ""}

STICKER_MAP = load_stickers()

# Tạo Enum động (Dynamic Enum) từ các Key trong file JSON để cấp cho LLM
EmotionType = Enum('EmotionType', {k: k for k in STICKER_MAP.keys()})

def get_sticker_id(emotion: str) -> Optional[str]:
    """Lấy Sticker ID từ key cảm xúc (trả về None nếu không map được)."""
    emotion = emotion.strip().upper()
    return STICKER_MAP.get(emotion) if emotion != "NONE" else None
