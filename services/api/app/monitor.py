"""Data freshness and uptime monitoring (P8 W11).

Rules (pure, unit-tested in tests/test_monitor.py):
- feed_stale:     no message from a source (SIM, ITMS, CROWD, FIELD) for STALE_S seconds
- junction_dark:  every approach of one junction silent for STALE_S while the feed itself is alive
- impossible:     a value no real signal can have: seconds remaining < 0 or > MAX_CYCLE_S, or a
                  green that lasted less than MIN_GREEN_S before changing
An alert opens once and closes itself when the condition clears. Notifications go to the API log,
and also to email (SMTP_*) and a Telegram bot (TELEGRAM_*) when those are configured (off by default).

Uptime: every minute the API probes itself, the database, Redis and the live feed and stores one row
per service (uptime_checks); the dashboard shows the daily uptime % (the 30-day, 99% goal).
"""

import asyncio
import contextlib
import logging
import smtplib
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from email.message import EmailMessage

import httpx
from sqlalchemy import Integer, func, insert, select, update

from . import db
from .config import settings
from .tables import alerts, uptime_checks

log = logging.getLogger("haribatti.monitor")
STALE_S = 30.0
MIN_GREEN_S = 3.0
MAX_CYCLE_S = 300.0
SERVICES = ("api", "database", "redis", "signal_feed")


@dataclass
class Event:
    key: str  # stable id of the condition, e.g. "feed_stale:SIM" or "junction_dark:J05"
    kind: str
    opened: bool  # True = alert opens, False = it clears
    message: str
    source: str | None = None
    junction: str | None = None


@dataclass
class FreshnessRules:
    stale_s: float = STALE_S
    last_by_source: dict[str, float] = field(default_factory=dict)
    last_by_approach: dict[str, float] = field(default_factory=dict)
    junction_of: dict[str, str] = field(default_factory=dict)
    green_since: dict[str, float] = field(default_factory=dict)
    colour: dict[str, str] = field(default_factory=dict)
    open: set[str] = field(default_factory=set)

    def observe(self, msg: dict, now: float) -> list[Event]:
        """One PhaseState arrives. Returns alerts for impossible values (they are one-off events)."""
        src, ap = msg.get("source", "?"), msg.get("approachId", "?")
        self.last_by_source[src] = now
        self.last_by_approach[ap] = now
        self.junction_of[ap] = msg.get("junctionId", ap[:3])
        out: list[Event] = []
        rem = msg.get("secondsRemaining")
        if isinstance(rem, int | float) and not (0 <= rem <= MAX_CYCLE_S):
            out.append(
                Event(
                    f"impossible:{ap}:remaining",
                    "impossible",
                    True,
                    f"{ap}: {rem} s remaining is impossible (0–{MAX_CYCLE_S:.0f} s)",
                    src,
                    self.junction_of[ap],
                )
            )
        prev, now_colour = self.colour.get(ap), msg.get("colour")
        if now_colour != prev:
            if prev == "GREEN" and ap in self.green_since:
                green = now - self.green_since.pop(ap)
                if green < MIN_GREEN_S:
                    out.append(
                        Event(
                            f"impossible:{ap}:green",
                            "impossible",
                            True,
                            f"{ap}: green lasted {green:.1f} s (< {MIN_GREEN_S:.0f} s)",
                            src,
                            self.junction_of[ap],
                        )
                    )
            if now_colour == "GREEN":
                self.green_since[ap] = now
            self.colour[ap] = now_colour
        return out

    def evaluate(self, now: float) -> list[Event]:
        """Open or close the stale / dark alerts."""
        out: list[Event] = []
        live_sources = set()
        for src, t in self.last_by_source.items():
            stale = now - t > self.stale_s
            if not stale:
                live_sources.add(src)
            out += self._flip(f"feed_stale:{src}", stale, Event(f"feed_stale:{src}", "feed_stale", stale,
                              f"No {src} data for {now - t:.0f} s" if stale else f"{src} data is flowing again", src))  # fmt: skip
        by_junction: dict[str, list[float]] = {}
        for ap, t in self.last_by_approach.items():
            by_junction.setdefault(self.junction_of[ap], []).append(t)
        for j, times in by_junction.items():
            dark = bool(live_sources) and all(now - t > self.stale_s for t in times)
            out += self._flip(f"junction_dark:{j}", dark, Event(f"junction_dark:{j}", "junction_dark", dark,
                              f"{j}: no approach reported for over {self.stale_s:.0f} s" if dark else f"{j} is reporting again", junction=j))  # fmt: skip
        return out

    def _flip(self, key: str, active: bool, ev: Event) -> list[Event]:
        if active and key not in self.open:
            self.open.add(key)
            return [ev]
        if not active and key in self.open:
            self.open.discard(key)
            return [ev]
        return []


# ---- notifications -------------------------------------------------------------------------------


def notify(ev: Event) -> None:
    """Log always; email and Telegram only when configured."""
    s = settings()
    text = f"[HariBatti] {'ALERT' if ev.opened else 'CLEARED'} {ev.kind}: {ev.message}"
    (log.warning if ev.opened else log.info)(text)
    if s.smtp_host and s.alert_email_to:
        try:
            m = EmailMessage()
            m["Subject"], m["From"], m["To"] = text[:120], s.smtp_from or s.smtp_user, s.alert_email_to
            m.set_content(text)
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as smtp:
                smtp.starttls()
                if s.smtp_user:
                    smtp.login(s.smtp_user, s.smtp_password)
                smtp.send_message(m)
        except (OSError, smtplib.SMTPException) as e:
            log.error("alert email not sent: %s", e)
    if s.telegram_bot_token and s.telegram_chat_id:
        try:
            httpx.post(
                f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
                json={"chat_id": s.telegram_chat_id, "text": text},
                timeout=10,
            )
        except httpx.HTTPError as e:
            log.error("alert Telegram message not sent: %s", e.__class__.__name__)


def store(ev: Event) -> None:
    """Open a row, or close the open row with the same key."""
    with db.connect() as c:
        if ev.opened:
            c.execute(
                insert(alerts).values(
                    key=ev.key, kind=ev.kind, source=ev.source, junction_id=ev.junction, message=ev.message
                )
            )
            if ev.kind == "impossible":  # one-off: opened and closed at once
                c.execute(
                    update(alerts)
                    .where(alerts.c.key == ev.key, alerts.c.closed_at.is_(None))
                    .values(closed_at=func.now())
                )
        else:
            c.execute(
                update(alerts)
                .where(alerts.c.key == ev.key, alerts.c.closed_at.is_(None))
                .values(closed_at=func.now())
            )


# ---- runner --------------------------------------------------------------------------------------


class Monitor:
    """Background tasks: watch the live hub, evaluate rules every 5 s, probe uptime every minute."""

    def __init__(self, hub, record: bool):
        self.hub, self.record = hub, record
        self.rules = FreshnessRules()
        self.started = time.monotonic()
        self.tasks: list[asyncio.Task] = []

    def start(self) -> None:
        self.tasks = [
            asyncio.create_task(self._watch()),
            asyncio.create_task(self._evaluate()),
            asyncio.create_task(self._uptime()),
        ]

    async def stop(self) -> None:
        for t in self.tasks:
            t.cancel()
        for t in self.tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await t

    async def _emit(self, events: list[Event]) -> None:
        for ev in events:
            await asyncio.to_thread(notify, ev)
            if self.record:
                try:
                    await asyncio.to_thread(store, ev)
                except Exception as e:  # noqa: BLE001 - monitoring must not crash the API
                    log.debug("alert not stored: %s", e)

    async def _watch(self) -> None:
        q = self.hub.subscribe()
        try:
            while True:
                msg = await q.get()
                await self._emit(self.rules.observe(msg, time.monotonic()))
        finally:
            self.hub.unsubscribe(q)

    async def _evaluate(self) -> None:
        while True:
            await asyncio.sleep(5)
            await self._emit(self.rules.evaluate(time.monotonic()))

    def feed_fresh(self) -> bool:
        now = time.monotonic()
        return any(now - t <= self.rules.stale_s for t in self.rules.last_by_source.values())

    async def _uptime(self) -> None:
        while True:
            if self.record:
                try:
                    await asyncio.to_thread(self._probe)
                except Exception as e:  # noqa: BLE001
                    log.debug("uptime probe not stored: %s", e)
            await asyncio.sleep(60)

    def _probe(self) -> None:
        results = {
            "api": True,
            "database": db.db_available(),
            "redis": redis_ok(),
            "signal_feed": self.feed_fresh(),
        }
        with db.connect() as c:
            c.execute(insert(uptime_checks), [{"service": k, "ok": v} for k, v in results.items()])


def redis_ok() -> bool:
    import redis

    try:
        return bool(redis.Redis.from_url(settings().redis_url, socket_timeout=2).ping())
    except Exception:  # noqa: BLE001 - any failure = down
        return False


def uptime_days(days: int = 30, today: date | None = None) -> dict:
    """Daily uptime % per service for the last `days` days (only days with checks)."""
    today = today or datetime.now(UTC).date()
    since = datetime.combine(today - timedelta(days=days - 1), datetime.min.time(), UTC)
    day = func.date_trunc("day", uptime_checks.c.ts)
    q = (select(uptime_checks.c.service, day.label("day"), func.count().label("n"), func.sum(func.cast(uptime_checks.c.ok, Integer)).label("ok"))
         .where(uptime_checks.c.ts >= since).group_by(uptime_checks.c.service, day).order_by(day))  # fmt: skip
    out: dict[str, list[dict]] = {s: [] for s in SERVICES}
    with db.connect() as c:
        for r in c.execute(q):
            out.setdefault(r.service, []).append(
                {
                    "day": r.day.date().isoformat(),
                    "checks": r.n,
                    "uptimePct": round(100 * (r.ok or 0) / r.n, 2),
                }
            )
    overall = {}
    for s, rows in out.items():
        n = sum(r["checks"] for r in rows)
        overall[s] = round(sum(r["uptimePct"] * r["checks"] for r in rows) / n, 2) if n else None
    return {"days": days, "services": out, "overall": overall, "goalPct": 99.0}
