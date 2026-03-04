"""
Background scheduler for proactive routines.

Uses APScheduler to run Agent briefings at user-configured times.
Designed for a Personal Agent (single user).
"""

import logging
from datetime import timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.core.database import get_supabase_client
from app.core.zalo import send_agent_response_to_zalo, send_zalo_message
from app.background.temp_cleanup import cleanup_temp_files

logger = logging.getLogger(__name__)

# Vietnam timezone (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

# Singleton scheduler instance
scheduler = AsyncIOScheduler(timezone=VN_TZ)

# ── Prompt templates for each routine type ───────────────
MORNING_PROMPT = (
    "[SYSTEM AUTO-TRIGGER] Đây là báo cáo buổi sáng tự động. "
    "Hãy thực hiện tuần tự: "
    "1) Kiểm tra lịch học hôm nay, "
    "2) Rà soát các task đến hạn hoặc sắp đến hạn, "
    "3) Kiểm tra sự kiện trong lịch hôm nay, "
    "4) Lấy thời tiết hiện tại tại Trà Vinh. "
    "Dựa trên tất cả thông tin, viết một báo cáo ngắn gọn, thân thiện, "
    "nhắc nhở chuẩn bị cho ngày mới. Format đẹp với emoji."
)

EVENING_PROMPT = (
    "[SYSTEM AUTO-TRIGGER] Đây là tổng kết buổi tối tự động. "
    "Hãy thực hiện tuần tự: "
    "1) Tổng kết các task đã hoàn thành hôm nay, "
    "2) Liệt kê task còn dang dở hoặc quá hạn, "
    "3) Xem trước lịch học ngày mai, "
    "4) Kiểm tra thời tiết ngày mai tại Trà Vinh. "
    "Viết một báo cáo ngắn gọn, nhẹ nhàng, "
    "nhắc nhở chuẩn bị cho ngày mai và chúc ngủ ngon. Format đẹp với emoji."
)


def _get_owner_user_id() -> str | None:
    """Get the single owner's user_id from the database.
    
    Personal agent: designed for single-user. Gets the primary user.
    """
    try:
        db = get_supabase_client()
        result = db.table("users").select("id").order("created_at", desc=False).limit(1).execute()
        if result.data:
            return result.data[0]["id"]
    except Exception as e:
        logger.error(f"Failed to get owner user_id: {e}")
    return None


def _get_user_preferences(user_id: str) -> dict:
    """Get user preferences from DB."""
    try:
        db = get_supabase_client()
        result = (
            db.table("users")
            .select("preferences")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return result.data.get("preferences", {}) if result.data else {}
    except Exception:
        return {}


async def _execute_routine(routine_type: str):
    """Core routine execution: run agent graph and send Zalo notification.

    Args:
        routine_type: "morning" or "evening"
    """
    logger.info(f"⏰ Executing {routine_type} routine...")

    user_id = _get_owner_user_id()
    if not user_id:
        logger.error("No user found in DB, skipping routine.")
        return

    # Check if routine is still enabled (user might have disabled it after scheduler started)
    prefs = _get_user_preferences(user_id)
    time_key = f"{routine_type}_routine_time"
    if not prefs.get(time_key):
        logger.info(f"{routine_type} routine disabled in preferences, skipping.")
        return

    try:
        # Import here to avoid circular imports
        from langchain_core.messages import HumanMessage
        from app.features.agent.graph import get_agent_graph
        from app.features.agent.memory import MemoryManager
        from datetime import datetime

        db = get_supabase_client()
        memory = MemoryManager(db, user_id)

        # 1. Thu thập Context
        today_date = datetime.now(VN_TZ).strftime("%d/%m/%Y")
        default_location, _ = memory.get_weather_prefs()
        user_location = default_location or "Trà Vinh"

        # 2. Get custom prompt or fallback
        raw_prompt = prefs.get(f"{routine_type}_routine_prompt")
        if not raw_prompt or not str(raw_prompt).strip():
            raw_prompt = MORNING_PROMPT if routine_type == "morning" else EVENING_PROMPT

        # 3. Interpolation
        final_prompt = raw_prompt.replace("{{current_date}}", today_date)
        final_prompt = final_prompt.replace("{{location}}", user_location)

        # Create a dedicated session for the routine
        session = memory.get_or_create_session()
        session_id = session["id"]

        # Build state for the agent
        state = {
            "messages": [HumanMessage(content=final_prompt)],
            "user_id": user_id,
            "user_name": memory.get_user_name(),
            "user_preferences": memory.get_user_preferences(),
            "user_location": None,
            "default_location": default_location,
            "conversation_summary": "",
            "platform": "zalo",  # Báo cáo gửi qua Zalo → LLM viết plain text
        }

        # Run agent graph
        settings = get_settings()
        graph = get_agent_graph()
        result = await graph.ainvoke(
            state,
            config={"recursion_limit": settings.AGENT_RECURSION_LIMIT},
        )

        # Extract response text
        from langchain_core.messages import AIMessage as _AIMessage
        ai_message = next(
            (m for m in reversed(result["messages"]) if isinstance(m, _AIMessage)),
            result["messages"][-1],
        )
        response_content = ai_message.content
        if isinstance(response_content, list):
            text_parts = []
            for part in response_content:
                if isinstance(part, str) and part:
                    text_parts.append(part)
                elif isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
            response_text = "\n".join(p for p in text_parts if p)
        else:
            response_text = str(response_content)

        # Save to chat history so it appears in the web UI
        title_prefix = "🌅 Báo cáo sáng" if routine_type == "morning" else "🌙 Tổng kết tối"
        memory.save_message(session_id, "user", f"[Auto] {title_prefix}")
        memory.save_message(session_id, "assistant", response_text)

        # Set session title
        db.table("conversation_sessions").update(
            {"title": title_prefix}
        ).eq("id", session_id).execute()

        # Send via Zalo Bot (format markdown → plain text trước khi gửi)
        from app.core.zalo_formatter import ZaloFormatter
        from app.core.zalo import send_zalo_photo
        import asyncio
        zalo_text = f"{title_prefix}\n\n{response_text}"
        image_urls, clean_zalo_text = ZaloFormatter.extract_images_and_clean(zalo_text)
        for img_url in image_urls:
            await send_zalo_photo(img_url)
            await asyncio.sleep(0.5)
        await send_agent_response_to_zalo(clean_zalo_text)

        logger.info(f"✅ {routine_type} routine completed successfully.")

    except Exception as e:
        logger.error(f"❌ {routine_type} routine failed: {e}", exc_info=True)
        # Try to notify via Zalo even on failure
        await send_zalo_message(f"⚠️ JARVIS: {routine_type} routine gặp lỗi: {str(e)[:200]}")


async def run_morning_briefing():
    """Callback for APScheduler morning job."""
    await _execute_routine("morning")


async def run_evening_review():
    """Callback for APScheduler evening job."""
    await _execute_routine("evening")


def update_routine_schedule(job_id: str, time_str: str | None):
    """Add, update, or remove a routine schedule.

    Args:
        job_id: "morning_routine_job" or "evening_routine_job"
        time_str: Time in "HH:MM" format, or None to disable.
    """
    if not time_str:
        # User disabled the routine
        try:
            scheduler.remove_job(job_id)
            logger.info(f"🔕 Removed scheduled job: {job_id}")
        except Exception:
            pass  # Job didn't exist, that's fine
        return

    # Parse time
    try:
        hour, minute = map(int, time_str.split(":"))
    except (ValueError, AttributeError):
        logger.error(f"Invalid time format '{time_str}', expected HH:MM")
        return

    # Determine callback
    func = run_morning_briefing if job_id == "morning_routine_job" else run_evening_review

    scheduler.add_job(
        func=func,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=VN_TZ),
        id=job_id,
        replace_existing=True,
    )
    logger.info(f"🔔 Scheduled {job_id} at {time_str} (Asia/Ho_Chi_Minh)")


def init_scheduler():
    """Initialize scheduler with user's saved preferences.

    Called during FastAPI lifespan startup.
    """
    user_id = _get_owner_user_id()
    if not user_id:
        logger.warning("No user found, scheduler has no jobs to register.")
        scheduler.start()
        return

    prefs = _get_user_preferences(user_id)

    morning_time = prefs.get("morning_routine_time")
    evening_time = prefs.get("evening_routine_time")

    if morning_time:
        update_routine_schedule("morning_routine_job", morning_time)
    if evening_time:
        update_routine_schedule("evening_routine_job", evening_time)

    scheduler.start()

    jobs = scheduler.get_jobs()
    if jobs:
        logger.info(f"📅 Scheduler started with {len(jobs)} job(s):")
        for job in jobs:
            logger.info(f"   - {job.id}: next run at {job.next_run_time}")
    else:
        logger.info("📅 Scheduler started (no active routines configured)")
        
    # Gọi Sync 1 lần ngay khi khởi động
    sync_dynamic_jobs()


def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("📅 Scheduler shut down.")

# ── Dynamic AI Cronjobs ──────────────────────────────────
async def run_dynamic_prompt_job(user_id: str, prompt: str, job_name: str):
    """Callback for dynamic cronjobs. Runs the agent with the given prompt."""
    logger.info(f"⚡ [AI CRON] Executing dynamic job: {job_name}")
    try:
        from langchain_core.messages import HumanMessage
        from app.features.agent.graph import get_agent_graph
        from app.features.agent.memory import MemoryManager
        
        db = get_supabase_client()
        memory = MemoryManager(db, user_id)
        session = memory.get_or_create_session()
        
        state = {
            "messages": [HumanMessage(content=prompt)],
            "user_id": user_id,
            "user_name": memory.get_user_name(),
            "user_preferences": memory.get_user_preferences(),
            "user_location": None,
            "default_location": "Trà Vinh",
            "conversation_summary": "",
            "platform": "web",
        }
        
        settings = get_settings()
        graph = get_agent_graph()
        await graph.ainvoke(state, config={"recursion_limit": settings.AGENT_RECURSION_LIMIT})
        logger.info(f"✅ [AI CRON] Job {job_name} finished.")
    except Exception as e:
        logger.error(f"❌ [AI CRON] Job {job_name} failed: {e}")

def sync_dynamic_jobs():
    """Quét Database bảng scheduled_prompts và nạp lại vào APScheduler."""
    try:
        db = get_supabase_client()
        res = db.table("scheduled_prompts").select("*").eq("is_active", True).execute()
        jobs = res.data or []
        
        # Xóa các job cũ có tiền tố dynamic_
        for job in scheduler.get_jobs():
            if job.id.startswith("dynamic_"):
                scheduler.remove_job(job.id)
                
        # Nạp lại
        for job in jobs:
            job_id = f"dynamic_{job['id']}"
            cron_expr = job["cron_expr"].split()
            if len(cron_expr) == 5:
                minute, hour, day, month, day_of_week = cron_expr
                scheduler.add_job(
                    func=run_dynamic_prompt_job,
                    trigger=CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week, timezone=VN_TZ),
                    args=[job["user_id"], job["prompt"], job["name"]],
                    id=job_id,
                    replace_existing=True
                )
        logger.info(f"🔄 Đã đồng bộ {len(jobs)} Dynamic AI Cronjobs từ Database.")
    except Exception as e:
        logger.error(f"Lỗi khi sync_dynamic_jobs: {e}")

# Chạy sync mỗi 5 phút một lần để update thay đổi ở DB
scheduler.add_job(sync_dynamic_jobs, 'interval', minutes=5, id="sync_dynamic_jobs_task", replace_existing=True)

# Dọn file tạm /temp/ trên S3 mỗi 6 giờ — xóa file > 24 giờ tuổi
scheduler.add_job(cleanup_temp_files, 'interval', hours=6, id="cleanup_temp_files_task", replace_existing=True)
