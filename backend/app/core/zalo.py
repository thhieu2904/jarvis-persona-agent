"""
Zalo Bot notification service.

Sends push notifications via Zalo Bot API (sendMessage).
Docs: https://bot.zaloplatforms.com/docs/
"""

import logging
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

ZALO_API_BASE = "https://bot-api.zaloplatforms.com"


async def send_zalo_message(text: str, chat_id: str | None = None) -> bool:
    """Send a text message via Zalo Bot.

    Args:
        text: Message content (max 2000 chars).
        chat_id: Recipient chat ID. Defaults to ZALO_CHAT_ID from config.

    Returns:
        True if sent successfully, False otherwise.
    """
    settings = get_settings()

    token = settings.ZALO_BOT_TOKEN
    recipient = chat_id or settings.ZALO_CHAT_ID

    if not token or not recipient:
        logger.warning("Zalo Bot not configured (missing ZALO_BOT_TOKEN or ZALO_CHAT_ID)")
        return False

    url = f"{ZALO_API_BASE}/bot{token}/sendMessage"

    # Zalo limits to 2000 chars per message
    if len(text) > 2000:
        text = text[:1997] + "..."

    payload = {
        "chat_id": recipient,
        "text": text,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload)
            data = response.json()

            if data.get("ok"):
                logger.info(f"✅ Zalo message sent (msg_id: {data['result'].get('message_id', 'N/A')})")
                return True
            else:
                logger.error(f"❌ Zalo API error: {data}")
                return False
    except Exception as e:
        logger.error(f"❌ Failed to send Zalo message: {e}")
        return False


async def send_zalo_sticker(sticker_id: str, chat_id: str | None = None) -> bool:
    """Send a sticker via Zalo Bot.

    Args:
        sticker_id: ID of the sticker from Zalo source.
        chat_id: Recipient chat ID. Defaults to ZALO_CHAT_ID.
    """
    settings = get_settings()
    token = settings.ZALO_BOT_TOKEN
    recipient = chat_id or settings.ZALO_CHAT_ID

    if not token or not recipient:
        return False

    url = f"{ZALO_API_BASE}/bot{token}/sendSticker"
    payload = {
        "chat_id": recipient,
        "sticker": sticker_id
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
            data = response.json()
            if data.get("ok"):
                logger.info(f"✅ Zalo sticker sent")
                return True
            else:
                logger.error(f"❌ Zalo sticker error: {data}")
                return False
    except Exception as e:
        logger.error(f"❌ Failed to send Zalo sticker: {e}")
        return False


async def send_zalo_photo(photo_url: str, caption: str = "",
                          chat_id: str | None = None) -> bool:
    """Send an image via Zalo Bot sendPhoto API.

    Args:
        photo_url: Public URL of the image (must be accessible from Zalo servers).
        caption: Optional caption (text shown below image, max ~1000 chars).
        chat_id: Recipient chat ID. Defaults to ZALO_CHAT_ID.
    """
    settings = get_settings()
    token = settings.ZALO_BOT_TOKEN
    recipient = chat_id or settings.ZALO_CHAT_ID

    if not token or not recipient:
        return False

    url = f"{ZALO_API_BASE}/bot{token}/sendPhoto"
    payload: dict = {"chat_id": recipient, "photo": photo_url}
    if caption:
        payload["caption"] = caption[:1000]

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload)
            data = response.json()
            if data.get("ok"):
                logger.info(f"✅ Zalo photo sent: {photo_url[:60]}")
                return True
            else:
                logger.error(f"❌ Zalo sendPhoto error: {data}")
                return False
    except Exception as e:
        logger.error(f"❌ Failed to send Zalo photo: {e}")
        return False


async def send_agent_response_to_zalo(text: str, chat_id: str | None = None) -> bool:
    """
    Thin LLM chain: Đọc đoạn hội thoại, quyết định Cảm xúc (Emotion), gửi Sticker (nếu có) trước khi gửi Text.
    """
    from pydantic import BaseModel, Field
    from app.core.llm_provider import create_llm
    from app.core.zalo_formatter import EmotionType, get_sticker_id
    import asyncio

    # Định nghĩa cấu trúc ép LLM trả về đúng Enum Emotion
    class EmotionResponse(BaseModel):
        emotion: EmotionType = Field(
            description="Lựa chọn cảm xúc thể hiện tốt nhất nội dung tin nhắn. Chọn NONE nếu là tin nhắn thông tin / báo cáo bình thường."
        )

    try:
        # Dùng LLM đánh giá cảm xúc
        llm = create_llm()
        structured_llm = llm.with_structured_output(EmotionResponse)
        
        prompt = (
            f"Phân tích cảm xúc của đoạn tin nhắn tiếng Việt sau đây:\n\n"
            f"\"{text}\"\n\n"
            f"Trả về loại cảm xúc tương ứng. Chọn NONE nếu không có sắc thái rõ ràng."
        )
        
        result = await structured_llm.ainvoke(prompt)
        emotion_val = result.emotion.value
        
        # Nếu có Sticker được map
        sticker_id = get_sticker_id(emotion_val)
        if sticker_id:
            await send_zalo_sticker(sticker_id, chat_id)
            await asyncio.sleep(0.3)  # Chờ Zalo nhận Sticker trước khi nhận Text
            
        # Gửi Text
        return await send_zalo_message(text, chat_id)

    except Exception as e:
        logger.error(f"Lỗi Thin LLM phân tích cảm xúc: {e}")
        # Luôn fallback về gửi text thường nếu LLM gặp lỗi (không load được schema, hết quota...)
        return await send_zalo_message(text, chat_id)
