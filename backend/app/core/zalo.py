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
