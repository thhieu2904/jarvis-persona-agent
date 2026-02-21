"""
Calendar feature: Service layer for calendar event management.
"""

from datetime import datetime, timedelta
from supabase import Client


class CalendarService:
    """CRUD operations for calendar events with date range queries."""

    def __init__(self, db: Client):
        self.db = db

    def create_event(
        self,
        user_id: str,
        title: str,
        start_time: str,
        end_time: str | None = None,
        description: str | None = None,
        event_type: str = "personal",
        is_all_day: bool = False,
        location: str | None = None,
        source: str = "user",
        reminder_minutes: int | None = None,
    ) -> dict:
        """Create a new calendar event (embedding = NULL, filled by bg job later)."""
        insert_data = {
            "user_id": user_id,
            "title": title,
            "description": description,
            "event_type": event_type,
            "start_time": start_time,
            "end_time": end_time,
            "is_all_day": is_all_day,
            "location": location,
            "source": source,
            "reminder_minutes": reminder_minutes,
        }
        result = self.db.table("calendar_events").insert(insert_data).execute()
        return result.data[0]

    def get_events(
        self,
        user_id: str,
        date: str | None = None,
        event_type: str | None = None,
        days_range: int = 7,
    ) -> list[dict]:
        """Get events for a user within a date range.
        
        Args:
            user_id: User's UUID
            date: Start date (YYYY-MM-DD), defaults to today
            event_type: Filter by event type
            days_range: Number of days to look ahead (default 7)
        """
        if date:
            start_date = date
        else:
            start_date = datetime.now().strftime("%Y-%m-%d")

        # Calculate end date
        end_dt = datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=days_range)
        end_date = end_dt.strftime("%Y-%m-%dT23:59:59")
        start_date_full = f"{start_date}T00:00:00"

        query = (
            self.db.table("calendar_events")
            .select("*")
            .eq("user_id", user_id)
            .gte("start_time", start_date_full)
            .lte("start_time", end_date)
        )

        if event_type:
            query = query.eq("event_type", event_type)

        result = query.order("start_time", desc=False).execute()
        return result.data

    def get_event_by_id(self, user_id: str, event_id: str) -> dict | None:
        """Get a single event by ID."""
        result = (
            self.db.table("calendar_events")
            .select("*")
            .eq("id", event_id)
            .eq("user_id", user_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def update_event(self, user_id: str, event_id: str, update_data: dict) -> dict | None:
        """Update an existing event."""
        clean_data = {k: v for k, v in update_data.items() if v is not None}
        if not clean_data:
            return None

        result = (
            self.db.table("calendar_events")
            .update(clean_data)
            .eq("id", event_id)
            .eq("user_id", user_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def delete_event(self, user_id: str, event_id: str) -> None:
        """Hard delete an event."""
        (
            self.db.table("calendar_events")
            .delete()
            .eq("id", event_id)
            .eq("user_id", user_id)
            .execute()
        )
