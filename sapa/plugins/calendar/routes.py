"""Calendar plugin routes."""

import logging
import time
import urllib.request
from datetime import datetime, date, timedelta

from fastapi import APIRouter
from icalendar import Calendar
import recurring_ical_events
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level state (set by plugin on_startup)
ics_url: str | None = None
_cached_events: list[dict] | None = None
_cache_time: float = 0
CACHE_TTL = 300  # 5 minutes

TZ = ZoneInfo("America/Chicago")


def _fetch_and_parse(start: date, end: date) -> list[dict]:
    """Fetch ICS feed and return events in the given date range."""
    if not ics_url:
        return []

    req = urllib.request.Request(ics_url, headers={"User-Agent": "SAPA/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()

    cal = Calendar.from_ical(raw)
    events = recurring_ical_events.of(cal).between(start, end)

    result = []
    for event in events:
        dtstart = event.get("DTSTART")
        dtend = event.get("DTEND")
        if not dtstart:
            continue

        start_val = dtstart.dt
        end_val = dtend.dt if dtend else None
        all_day = isinstance(start_val, date) and not isinstance(start_val, datetime)

        if all_day:
            start_str = start_val.isoformat()
            end_str = end_val.isoformat() if end_val else start_str
        else:
            if start_val.tzinfo is None:
                start_val = start_val.replace(tzinfo=TZ)
            start_local = start_val.astimezone(TZ)
            start_str = start_local.isoformat()

            if end_val:
                if end_val.tzinfo is None:
                    end_val = end_val.replace(tzinfo=TZ)
                end_local = end_val.astimezone(TZ)
                end_str = end_local.isoformat()
            else:
                end_str = start_str

        result.append({
            "summary": str(event.get("SUMMARY", "Untitled")),
            "start": start_str,
            "end": end_str,
            "location": str(event.get("LOCATION", "")) or None,
            "description": str(event.get("DESCRIPTION", "")) or None,
            "all_day": all_day,
        })

    # Sort: all-day first, then by start time
    result.sort(key=lambda e: (not e["all_day"], e["start"]))
    return result


def _get_today_events() -> list[dict]:
    """Get today's events with caching."""
    global _cached_events, _cache_time

    now = time.time()
    if _cached_events is not None and (now - _cache_time) < CACHE_TTL:
        return _cached_events

    today = date.today()
    tomorrow = today + timedelta(days=1)
    try:
        _cached_events = _fetch_and_parse(today, tomorrow)
        _cache_time = now
    except Exception as e:
        logger.error(f"Failed to fetch calendar: {e}")
        if _cached_events is not None:
            return _cached_events
        return []

    return _cached_events


@router.get("/events")
async def get_today_events():
    return _get_today_events()


@router.get("/events/week")
async def get_week_events():
    today = date.today()
    # Start from Monday of current week
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=7)
    try:
        return _fetch_and_parse(monday, sunday)
    except Exception as e:
        logger.error(f"Failed to fetch calendar week: {e}")
        return []


@router.post("/refresh")
async def refresh_calendar():
    global _cached_events, _cache_time
    _cached_events = None
    _cache_time = 0
    events = _get_today_events()
    return {"status": "ok", "events_today": len(events)}
