"""
Background cleanup job: Xóa file tạm trong S3 bucket `knowledge-base` sau 24 giờ.

Luồng tạo file tạm:
  POST /api/knowledge/extract-text → lưu vào `{user_id}/temp/{unix_ts}_{safe_filename}`

Luồng xóa:
  cleanup_temp_files() chạy mỗi 6 giờ theo APScheduler.
  List tất cả files trong thư mục /temp/ của mỗi user.
  Parse unix_ts từ tên file (phần tử đầu tiên trước dấu `_`).
  Nếu (now - ts) > MAX_AGE_SECONDS → xóa khỏi S3.
"""

import time
import logging
from datetime import timezone, timedelta

from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)

# 24 giờ (tính bằng giây)
MAX_AGE_SECONDS = 24 * 60 * 60


def _parse_timestamp_from_name(file_name: str) -> int | None:
    """
    Parse unix timestamp từ tên file có format: `{unix_ts}_{original_name}`.

    Returns:
        Unix timestamp (int) nếu parse được, None nếu không đúng format.
    """
    parts = file_name.split("_", 1)
    if len(parts) < 2:
        return None
    try:
        return int(parts[0])
    except (ValueError, TypeError):
        return None


def cleanup_temp_files() -> dict:
    """
    Xóa file tạm trong S3 bucket `knowledge-base/{user_id}/temp/` sau 24 giờ.

    Logic:
      1. Lấy tất cả user_id từ bảng users.
      2. Với mỗi user, list files trong prefix `{user_id}/temp/`.
      3. Parse unix_ts từ tên file.
      4. Xóa nếu tuổi file > MAX_AGE_SECONDS.
      5. Bỏ qua file không đúng format tên (không parse được ts) — không xóa nhầm.

    Returns:
        dict: { "deleted": int, "skipped": int, "errors": int }
    """
    stats = {"deleted": 0, "skipped": 0, "errors": 0}
    now = int(time.time())

    try:
        db = get_supabase_client()

        # Lấy tất cả user_id — single-user system, nhưng giữ generic
        users_res = db.table("users").select("id").execute()
        users = users_res.data or []

        for user in users:
            user_id = user["id"]
            prefix = f"{user_id}/temp"

            try:
                files = db.storage.from_("knowledge-base").list(prefix)
            except Exception as e:
                logger.warning(f"Could not list temp files for user {user_id}: {e}")
                stats["errors"] += 1
                continue

            if not files:
                continue

            for file_obj in files:
                file_name = file_obj.get("name", "")
                if not file_name:
                    continue

                ts = _parse_timestamp_from_name(file_name)
                if ts is None:
                    # Không đúng format `{ts}_{name}` → bỏ qua, không xóa nhầm
                    logger.debug(f"Skipping temp file with unrecognized format: {file_name}")
                    stats["skipped"] += 1
                    continue

                age_seconds = now - ts
                if age_seconds > MAX_AGE_SECONDS:
                    storage_path = f"{prefix}/{file_name}"
                    try:
                        db.storage.from_("knowledge-base").remove([storage_path])
                        logger.info(
                            f"🗑️  Deleted expired temp file: {storage_path} "
                            f"(age: {age_seconds // 3600}h)"
                        )
                        stats["deleted"] += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file {storage_path}: {e}")
                        stats["errors"] += 1
                else:
                    stats["skipped"] += 1

    except Exception as e:
        logger.error(f"cleanup_temp_files failed: {e}")
        stats["errors"] += 1

    logger.info(
        f"✅ Temp cleanup finished — "
        f"deleted={stats['deleted']}, skipped={stats['skipped']}, errors={stats['errors']}"
    )
    return stats
