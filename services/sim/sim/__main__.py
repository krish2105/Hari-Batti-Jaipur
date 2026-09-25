"""HariBatti simulator command line (`python -m sim <command>`; see `make sim*` targets).

  run        live 1 Hz PhaseState stream to Redis channel "signals" (default command)
  build      build network + signal plans + 24-h survey demand (cached)
  calibrate  headless run + GEH calibration/validation report (services/sim/reports/calibration.md)
  coords     look up CANDIDATE junction coordinates on OpenStreetMap (never edits the registry)
  simulate   Plan Studio what-if: baseline vs proposed plan, JSON output
The simulator is read-only: it never sends anything to a real signal.
"""

import argparse
import contextlib
import sys
from pathlib import Path

from . import config


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m sim", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd")

    r = sub.add_parser("run", help="live stream at 1 Hz")
    r.add_argument("--start", help="survey clock time HH:MM (default: now in Asia/Kolkata)")
    r.add_argument("--plan", default="demand2", choices=["demand2", "webster4", "even"])
    r.add_argument("--geometry", default="auto", choices=["auto", "schematic", "osm"])
    r.add_argument("--dry-run", action="store_true", help="print JSON to stdout instead of Redis")

    b = sub.add_parser("build", help="build simulation inputs")
    b.add_argument("--geometry", default="auto", choices=["auto", "schematic", "osm"])
    b.add_argument("--coords", type=Path, help="TEST ONLY: use a candidates CSV instead of the registry")
    b.add_argument("--force", action="store_true")

    c = sub.add_parser("calibrate", help="GEH calibration + validation report")
    c.add_argument("--hours", type=int, default=24)
    c.add_argument("--geometry", default="auto", choices=["auto", "schematic", "osm"])
    c.add_argument("--report-only", action="store_true", help="rebuild the report from the last run")

    sub.add_parser("coords", help="look up candidate coordinates on OpenStreetMap")

    s = sub.add_parser("simulate", help="Plan Studio: baseline vs proposed plan (JSON)")
    s.add_argument("--baseline", default="even", choices=["demand2", "webster4", "even"])
    s.add_argument("--proposed", default="demand2", choices=["demand2", "webster4", "even"])
    s.add_argument("--junction", help="junction for a custom plan, e.g. J05")
    s.add_argument("--custom", help='JSON: {"cycle_s": 90, "main_green_s": 50, "cross_green_s": 30}')
    s.add_argument("--start", default="18:15")
    s.add_argument("--minutes", type=int, default=15)
    s.add_argument("--warmup", type=int, default=5)

    args = p.parse_args(argv)
    cmd = args.cmd or "run"
    if cmd == "coords":
        from .coords_lookup import lookup

        lookup()
        return 0

    from .build import build

    if cmd == "simulate":
        from .simulate import main_json

        with contextlib.redirect_stdout(sys.stderr):  # keep stdout for the JSON result only
            args.build_dir = build("auto")
        main_json(args)
        return 0
    if cmd == "build":
        build(args.geometry, args.coords, args.force)
        return 0
    if cmd == "calibrate":
        from .calibrate import report_from_run, run_calibration

        out = build(args.geometry)
        if args.report_only:
            report_from_run(out)
        else:
            run_calibration(out, hours=args.hours)
        return 0

    from .clock import start_offset
    from .stream import RedisPublisher, StdoutPublisher, run

    start = getattr(args, "start", None)
    geometry = getattr(args, "geometry", "auto")
    plan = getattr(args, "plan", "demand2")
    out = build(geometry)
    publisher = StdoutPublisher() if getattr(args, "dry_run", False) else RedisPublisher(config.redis_url())
    run(out, start_offset(start), plan, publisher)
    return 0


if __name__ == "__main__":
    sys.exit(main())
