"""Map real time (India, Asia/Kolkata) to the survey day's simulation clock.

Sim time 0 s = 08:00 IST on the survey day; the day runs to 08:00 the next morning (86,400 s).
The Mac may be in another time zone (e.g. Dubai), so we always convert to IST first.
"""

from datetime import UTC, datetime

from .config import DAY_S, IST, SURVEY_DAY_START_HOUR


def parse_hhmm(text: str) -> int:
    """'18:15' -> seconds after midnight. Raises ValueError on bad input."""
    hh, _, mm = text.strip().partition(":")
    h, m = int(hh), int(mm or 0)
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"Bad time {text!r}; use HH:MM")
    return h * 3600 + m * 60


def clock_to_sim_offset(seconds_after_midnight: int) -> int:
    """Clock time of day (IST) -> seconds since the survey day's 08:00 start (wraps at 08:00)."""
    return (seconds_after_midnight - SURVEY_DAY_START_HOUR * 3600) % DAY_S


def start_offset(start: str | None, now_utc: datetime | None = None) -> int:
    """Where to begin the replay: START=HH:MM if given, else the current time of day in IST."""
    if start:
        return clock_to_sim_offset(parse_hhmm(start))
    now_ist = (now_utc or datetime.now(UTC)).astimezone(IST)
    return clock_to_sim_offset(now_ist.hour * 3600 + now_ist.minute * 60 + now_ist.second)


def sim_clock_label(sim_s: float, survey_date: str) -> str:
    """Sim seconds -> '18:15:03 IST, survey day 2026-05-11'."""
    t = int(sim_s + SURVEY_DAY_START_HOUR * 3600) % DAY_S
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d} IST, survey day {survey_date}"
