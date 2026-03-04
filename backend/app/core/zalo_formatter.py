"""
Zalo Formatter & Sticker mapping.

Đọc cấu hình JSON để map thẻ cảm xúc với ID Sticker.
Chứa ZaloFormatter để chuyển Markdown → plain text thân thiện Zalo.
"""

import os
import re
import json
from enum import Enum
from typing import Optional, Tuple, List

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

ZALO_SAFE_TEXT_LIMIT = 1900

def get_sticker_id(emotion: str) -> Optional[str]:
    """Lấy Sticker ID từ key cảm xúc (trả về None nếu không map được)."""
    emotion = emotion.strip().upper()
    return STICKER_MAP.get(emotion) if emotion != "NONE" else None


def split_text_for_zalo(text: str, limit: int = ZALO_SAFE_TEXT_LIMIT) -> List[str]:
    """Tách text thành nhiều phần an toàn cho Zalo sendMessage.

    Ưu tiên cắt theo ranh giới tự nhiên: đoạn, dòng, câu, từ.
    Fallback cuối cùng là cắt cứng theo limit.
    """
    if limit <= 0:
        raise ValueError("limit must be greater than 0")

    if not text:
        return []

    remaining = text.replace("\r\n", "\n").strip()
    if not remaining:
        return []

    chunks: List[str] = []
    sentence_separators = [". ", "! ", "? ", ".\n", "!\n", "?\n"]

    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break

        window = remaining[:limit]
        min_tail_position = max(limit // 2, 1)
        cut = -1

        paragraph_cut = window.rfind("\n\n")
        if paragraph_cut >= min_tail_position:
            cut = paragraph_cut + 2

        if cut == -1:
            line_cut = window.rfind("\n")
            if line_cut >= min_tail_position:
                cut = line_cut + 1

        if cut == -1:
            sentence_cut = -1
            sentence_offset = 0
            for separator in sentence_separators:
                idx = window.rfind(separator)
                if idx > sentence_cut and idx >= min_tail_position:
                    sentence_cut = idx
                    sentence_offset = len(separator)
            if sentence_cut != -1:
                cut = sentence_cut + sentence_offset

        if cut == -1:
            word_cut = window.rfind(" ")
            if word_cut >= min_tail_position:
                cut = word_cut + 1

        if cut == -1:
            cut = limit

        chunk = remaining[:cut].strip()
        if not chunk:
            chunk = remaining[:limit]
            cut = limit

        chunks.append(chunk)
        remaining = remaining[cut:].lstrip()

    return chunks


class ZaloFormatter:
    """Chuyển Markdown output của LLM sang plain text thân thiện với Zalo."""

    @staticmethod
    def extract_images_and_clean(markdown_text: str) -> Tuple[List[str], str]:
        """Tách URL ảnh từ Markdown và làm sạch text về plain text cho Zalo.

        Returns:
            (image_urls, clean_text)
            - image_urls: list URL ảnh dùng để gọi sendPhoto tuần tự
            - clean_text: plain text đã tước hết Markdown syntax
        """
        text = markdown_text

        # 1. Tách URL ảnh (chỉ lấy public URL, bỏ signed URL có ?token=)
        all_image_urls = re.findall(r'!\[.*?\]\((https?://[^)]+)\)', text)
        image_urls = [u for u in all_image_urls if '?token=' not in u and 'signedURL' not in u]

        # 2. Xóa tag ảnh ra khỏi text
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)

        # 3. Header: ### Tiêu đề → ▌ TIÊU ĐỀ
        text = re.sub(r'^#{1,6}\s+(.+)$', lambda m: f"▌ {m.group(1).upper()}", text, flags=re.MULTILINE)

        # 4. Bold: **text** hoặc __text__ → text
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)

        # 5. Italic: *text* hoặc _text_ → text
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)

        # 6. Code block: ```lang\ncode\n``` → [CODE]\ncode\n[/CODE]
        #    (MUST run before inline code to avoid ` stripping ``` outer backticks)
        text = re.sub(r'```[\w]*\n([\s\S]*?)```', r'[CODE]\n\1[/CODE]', text)
        text = re.sub(r'```([\s\S]*?)```', r'[CODE]\n\1\n[/CODE]', text)

        # 7. Inline code: `code` → code
        text = re.sub(r'`([^`]+)`', r'\1', text)

        # 8. Unordered list: "- item" / "* item" → "• item"
        text = re.sub(r'^[\s]*[-*]\s+', '• ', text, flags=re.MULTILINE)

        # 9. Markdown link: [text](url) → text (url)
        text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'\1 (\2)', text)

        # 10. Horizontal rule: --- hoặc *** → ─────────────
        text = re.sub(r'^[-*]{3,}\s*$', '─────────────', text, flags=re.MULTILINE)

        # 11. Blockquote: > text → "text
        text = re.sub(r'^>\s+', '"', text, flags=re.MULTILINE)

        # 12. Table separator: |---|---| → xóa
        text = re.sub(r'^\|[-:| ]+\|\s*$', '', text, flags=re.MULTILINE)

        # 13. Dọn khoảng trắng thừa: max 2 dòng trống liên tiếp
        text = re.sub(r'\n{3,}', '\n\n', text)

        return image_urls, text.strip()
