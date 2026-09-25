"""Live mode: run SUMO in real time and publish PhaseState JSON to Redis channel "signals" at 1 Hz.

One message per junction approach per second (8 junctions x 4 approaches = 32 messages).
Read-only by design: the simulator publishes signal states; nothing here listens for commands.
"""

import contextlib
import json
import signal
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import redis
import traci

from . import config
from .clock import sim_clock_label
from .config import load_assumptions
from .phase import ApproachLinks, approach_colour, choose_report_links, seconds_until_change, to_phase_state
from .registry import slug
from .sumo_env import binary
from .timings import PLAN_LABELS


class RedisPublisher:
    """Publishes to Redis; if Redis is down it keeps the sim running and retries with backoff."""

    def __init__(self, url: str):
        self.url = url
        self.client = redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        self.down_since: float | None = None
        self.next_try = 0.0

    def publish(self, messages: list[dict]) -> None:
        now = time.monotonic()
        if self.down_since is not None and now < self.next_try:
            return
        try:
            pipe = self.client.pipeline(transaction=False)
            for m in messages:
                pipe.publish(config.REDIS_CHANNEL, json.dumps(m, ensure_ascii=False))
            pipe.execute()
            if self.down_since is not None:
                print(f"[sim] Redis back at {self.url}; publishing again", flush=True)
            self.down_since = None
        except redis.RedisError as e:
            wait = 2.0 if self.down_since is None else min(30.0, (now - self.down_since) or 2.0)
            if self.down_since is None:
                self.down_since = now
            self.next_try = now + wait
            print(
                f"[sim] Redis not reachable at {self.url} ({e.__class__.__name__}); retry in {wait:.0f}s. "
                "Is `make infra` running?",
                flush=True,
            )


class StdoutPublisher:
    """--dry-run: print each message as one JSON line."""

    def publish(self, messages: list[dict]) -> None:
        for m in messages:
            print(json.dumps(m, ensure_ascii=False))
        sys.stdout.flush()


class ListPublisher:
    """For tests: keep every tick's messages in memory."""

    def __init__(self) -> None:
        self.ticks: list[list[dict]] = []

    def publish(self, messages: list[dict]) -> None:
        self.ticks.append(messages)


@dataclass
class SignalView:
    """What we need to report one junction: its SUMO program and the approaches to report."""

    junction_id: str
    tls_id: str
    phases: list[tuple[int, str]]
    approaches: list[ApproachLinks]
    timing: str
    timing_label: str


def sumo_command(build_dir: Path, plan: str, begin: int, extra: list[str] | None = None) -> list[str]:
    """The sumo command line shared by live mode and calibration."""
    a = load_assumptions()
    return [
        binary("sumo"),
        "-n",
        str(build_dir / "network.net.xml"),
        "-r",
        str(build_dir / "routes.rou.xml"),
        "-a",
        f"{build_dir / 'vtypes.add.xml'},{build_dir / f'tls_{plan}.add.xml'}",
        "--begin",
        str(begin),
        "--step-length",
        "1",
        "--lateral-resolution",
        str(a["sublane"]["lateral_resolution_m"]),
        "--no-step-log",
        "true",
        "--seed",
        "42",
        *(extra or []),
    ]


def signal_views(manifest: dict, plan: str) -> list[SignalView]:
    """Read each junction's active program from SUMO and pick the links to report per approach."""
    views = []
    for jid, apps in manifest["approaches"].items():
        tls = manifest["tls_ids"][jid]
        traci.trafficlight.setProgram(tls, "haribatti")
        logic = next(lg for lg in traci.trafficlight.getAllProgramLogics(tls) if lg.programID == "haribatti")
        links = {int(k): tuple(v) for k, v in manifest["links"][jid].items()}
        approaches = [
            ApproachLinks(jid, f"{jid}-{slug(name)}", name, choose_report_links(links, info["side"]))
            for name, info in apps.items()
        ]
        p = manifest["plans"][plan][jid]
        views.append(
            SignalView(
                jid,
                tls,
                [(int(ph.duration), ph.state) for ph in logic.phases],
                approaches,
                p["timing"],
                p["label"],
            )
        )
    return views


def tick_messages(views: list[SignalView], manifest: dict, sim_s: float, confidence: float) -> list[dict]:
    """PhaseState for every approach at the current simulation second."""
    now = datetime.now(UTC)
    label = sim_clock_label(sim_s, config.CALIBRATION_DATE)
    out = []
    for v in views:
        idx = traci.trafficlight.getPhase(v.tls_id)
        remaining = traci.trafficlight.getNextSwitch(v.tls_id) - sim_s
        state = traci.trafficlight.getRedYellowGreenState(v.tls_id)
        for ap in v.approaches:
            out.append(
                to_phase_state(
                    ap,
                    approach_colour(state, ap.link_indices),
                    seconds_until_change(v.phases, idx, remaining, ap.link_indices),
                    now,
                    confidence=confidence,
                    timing=v.timing,
                    timing_label=v.timing_label,
                    geometry=manifest["geometry"],
                    geometry_label=manifest["geometry_label"],
                    sim_clock=label,
                )
            )
    return out


def run(
    build_dir: Path, begin: int, plan: str, publisher, ticks: int | None = None, realtime: bool = True
) -> None:
    """Main loop. Wall-clock paced at 1 Hz unless realtime=False (tests). Wraps at the day's end."""
    manifest = json.loads((build_dir / "manifest.json").read_text(encoding="utf-8"))
    confidence = float(load_assumptions()["stream"]["confidence"])
    print(
        f"[sim] {manifest['geometry_label']} | {PLAN_LABELS[plan]} | "
        f"start {sim_clock_label(begin, config.CALIBRATION_DATE)} | channel '{config.REDIS_CHANNEL}'",
        flush=True,
    )
    for flag in manifest["flags"]:
        print(f"[sim]   ASSUMED: {flag}", flush=True)

    stop = False

    def _stop(*_):
        nonlocal stop
        stop = True

    old_handler = signal.signal(signal.SIGINT, _stop) if realtime else None
    done = 0
    try:
        while not stop:
            traci.start(sumo_command(build_dir, plan, begin, ["--no-warnings", "true"]))
            views = signal_views(manifest, plan)
            sim_s = float(begin)
            next_wall = time.monotonic()
            while not stop and sim_s < config.DAY_S:
                traci.simulationStep()
                sim_s = traci.simulation.getTime()
                publisher.publish(tick_messages(views, manifest, sim_s, confidence))
                done += 1
                if ticks is not None and done >= ticks:
                    return
                if realtime:
                    next_wall += 1.0
                    delay = next_wall - time.monotonic()
                    if delay > 0:
                        time.sleep(delay)
                    elif delay < -5:
                        print(f"[sim] running {-delay:.0f}s behind real time", flush=True)
                        next_wall = time.monotonic()
            traci.close()
            if not stop:
                begin = 0  # survey day finished: start again at 08:00
                print("[sim] survey day ended; restarting at 08:00 IST", flush=True)
    finally:
        with contextlib.suppress(traci.exceptions.FatalTraCIError, traci.exceptions.TraCIException):
            traci.close()  # may already be closed
        if old_handler is not None:
            signal.signal(signal.SIGINT, old_handler)
        print("[sim] stopped", flush=True)
