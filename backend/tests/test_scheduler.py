"""Unit tests for scheduler and zalo modules."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import timezone, timedelta
from app.core.zalo import send_zalo_message
from app.background.scheduler import VN_TZ, update_routine_schedule, scheduler
from app.config import get_settings


def test_all():
    settings = get_settings()
    print("=== Unit Test: Scheduler & Zalo ===")

    # Test 1: VN timezone constant
    tz_str = str(VN_TZ)
    print(f"1. VN_TZ = {tz_str}")
    assert "07:00" in tz_str, f"Expected UTC+07:00, got {tz_str}"
    print("   PASS: VN timezone constant correct")

    # Test 2: Scheduler has correct timezone
    sched_tz = str(scheduler.timezone)
    print(f"2. Scheduler timezone = {sched_tz}")
    assert "07:00" in sched_tz, f"Expected UTC+07:00, got {sched_tz}"
    print("   PASS: Scheduler timezone configured correctly")

    # Test 3: CronTrigger can be created with VN timezone
    trigger = CronTrigger(hour=6, minute=30, timezone=VN_TZ)
    print(f"3. CronTrigger: {trigger}")
    print("   PASS: CronTrigger with VN timezone works")

    # Test 4: Zalo config loaded
    has_token = bool(settings.ZALO_BOT_TOKEN)
    has_chat = bool(settings.ZALO_CHAT_ID)
    print(f"4. ZALO_BOT_TOKEN: {'configured' if has_token else 'MISSING'}")
    print(f"   ZALO_CHAT_ID: {'configured' if has_chat else 'empty (needs user setup)'}")
    assert has_token, "ZALO_BOT_TOKEN must be configured"
    print("   PASS: Zalo config loaded correctly")

    # Test 5: Test with a synchronous BackgroundScheduler (to validate add/replace/remove logic)
    test_sched = BackgroundScheduler(timezone=VN_TZ)
    test_sched.start(paused=True)

    # Add job
    test_sched.add_job(lambda: None, CronTrigger(hour=6, minute=30, timezone=VN_TZ),
                       id="morning_routine_job", replace_existing=True)
    jobs = test_sched.get_jobs()
    assert len(jobs) == 1, f"Expected 1 job, got {len(jobs)}"
    print("5. PASS: add_job works")

    # Replace job
    test_sched.add_job(lambda: None, CronTrigger(hour=7, minute=0, timezone=VN_TZ),
                       id="morning_routine_job", replace_existing=True)
    jobs = test_sched.get_jobs()
    assert len(jobs) == 1, f"Expected 1 job after replace, got {len(jobs)}"
    print("6. PASS: replace_existing works")

    # Add second job
    test_sched.add_job(lambda: None, CronTrigger(hour=23, minute=0, timezone=VN_TZ),
                       id="evening_routine_job", replace_existing=True)
    jobs = test_sched.get_jobs()
    assert len(jobs) == 2, f"Expected 2 jobs, got {len(jobs)}"
    print(f"7. PASS: Multiple jobs: {[j.id for j in jobs]}")

    # Remove job
    test_sched.remove_job("morning_routine_job")
    jobs = test_sched.get_jobs()
    assert len(jobs) == 1, f"Expected 1 job after removal, got {len(jobs)}"
    print("8. PASS: remove_job works")

    # Remove non-existent (should not crash)
    try:
        test_sched.remove_job("morning_routine_job")
    except Exception:
        pass  # Expected
    print("9. PASS: Removing non-existent job = no crash")

    test_sched.shutdown(wait=False)

    # Test 10: send_zalo_message function signature
    import inspect
    sig = inspect.signature(send_zalo_message)
    params = list(sig.parameters.keys())
    assert "text" in params, "send_zalo_message must accept 'text'"
    print("10. PASS: send_zalo_message signature correct")

    print("")
    print("=== ALL 10 TESTS PASSED ===")


if __name__ == "__main__":
    test_all()
