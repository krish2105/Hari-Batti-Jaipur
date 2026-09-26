"""Fixed-camera junction video -> counts, queues, saturation flow, signal state and pedestrians.

`make cv-video VIDEO=path.mp4 JUNCTION=J05` (camera profile: services/cv/profiles/<JUNCTION>.json).
Every frame that is written to disk (the preview video) is privacy-blurred first (privacy.py).
Outputs in services/cv/out/<JUNCTION>/ (gitignored):
  counts.csv               turning counts per movement and 15-min slot, tmc_clean.csv schema, source FIELD
  approach_volumes.csv     vehicles crossing each arm's count line (both directions), by survey class and PCU
  queues.csv               vehicles queued (stopped) per approach, every second
  saturation.json          measured saturation flow at the stop line (discharge headways, HCM method)
  signal_states.csv        lamp colour per second (only when the profile has a lamp ROI)
  signal_timings_field.csv green/amber durations in data/signal_timings.csv format, for REVIEW
  pedestrians.csv          people crossing the crosswalk zone and how long each crossing took
  quality.json             frame-rate, sharpness and brightness checks; numbers are withheld if poor
  preview.mp4              blurred, annotated preview (never the raw video)
Read-only: HariBatti watches a recording; it never touches a signal.
"""

import argparse
import csv
import itertools
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import supervision as sv

from .detector import COCO_IDS, Detector, class_names
from .paths import OUT, PROFILES, REPORTS
from .privacy import Blurrer

# survey classes (tmc_clean.csv columns) and the survey's own PCU factors (website: vehicle mix section)
UVH_TO_SURVEY = {
    "Hatchback": "car_taxi_auto_pickup", "Sedan": "car_taxi_auto_pickup", "SUV": "car_taxi_auto_pickup",
    "MUV": "car_taxi_auto_pickup", "Van": "car_taxi_auto_pickup", "Three-wheeler": "car_taxi_auto_pickup",
    "Others": "car_taxi_auto_pickup", "Two-wheeler": "two_wheeler", "LCV": "tractor_lcv_minibus",
    "Mini-bus": "tractor_lcv_minibus", "Tempo-traveller": "tractor_lcv_minibus", "Bus": "axle_truck_bus",
    "Truck": "axle_truck_bus", "Bicycle": "cycle",
}  # fmt: skip
PCU = {"two_wheeler": 0.5, "car_taxi_auto_pickup": 1.0, "tractor_lcv_minibus": 1.5, "axle_truck_bus": 3.0,
       "truck_trailer_mav": 4.5, "cycle": 0.5, "cycle_rickshaw": 1.5, "hand_cart": 3.0, "horse_drawn": 4.0,
       "bullock_cart": 8.0}  # fmt: skip
FAST = ["car_taxi_auto_pickup", "two_wheeler", "tractor_lcv_minibus", "axle_truck_bus", "truck_trailer_mav"]
SLOW = ["cycle", "cycle_rickshaw", "hand_cart", "horse_drawn", "bullock_cart"]
# turning targets for left-hand traffic: from arm side -> {turn: exit side}
TURN = {"S": {"L": "W", "S": "N", "R": "E"}, "N": {"L": "E", "S": "S", "R": "W"},
        "E": {"L": "S", "S": "W", "R": "N"}, "W": {"L": "N", "S": "E", "R": "S"}}  # fmt: skip
STOPPED_PX_S = (
    12  # a vehicle moving less than this many pixels per second counts as queued (scaled to 1080p width)
)
MIN_SHARPNESS = 40.0  # variance of the Laplacian below this = too blurry to trust
MIN_BRIGHTNESS = 45.0  # mean grey level below this = night / too dark
MIN_FPS = 10.0


def turn_of(frm: str, to: str) -> str | None:
    return next((t for t, s in TURN.get(frm, {}).items() if s == to), None)


def slot_of(clock_s: float) -> int:
    """Seconds since midnight -> survey slot (0 = 08:00-08:15 ... 95 = 07:45-08:00)."""
    return int(((clock_s / 900) - 32) % 96)


def side_of_line(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def crosses(p0, p1, a, b) -> bool:
    """Did the move p0 -> p1 cross segment a-b?"""
    s0, s1 = side_of_line(p0, a, b), side_of_line(p1, a, b)
    t0, t1 = side_of_line(a, p0, p1), side_of_line(b, p0, p1)
    return s0 * s1 < 0 and t0 * t1 < 0


def saturation_from_headways(
    times: list[float], queued: list[bool], skip: int = 4, max_gap: float = 3.0
) -> dict:
    """HCM discharge-headway method: in each queue discharge (consecutive stop-line crossings of vehicles
    that had been queued, gaps under max_gap s), ignore the first `skip` vehicles (start-up lost time)
    and average the remaining headways. Saturation flow = 3600 / mean headway (vehicles/h)."""
    heads: list[float] = []
    run: list[float] = []
    for t, q in zip(times + [math.inf], queued + [False], strict=True):
        if q and (not run or t - run[-1] <= max_gap):
            run.append(t)
            continue
        if len(run) > skip + 1:
            heads += [b - a for a, b in zip(run[skip:], run[skip + 1 :], strict=False)]
        run = [t] if q else []
    if len(heads) < 5:
        return {"measured": False, "headways": len(heads)}
    mean = float(np.mean(heads))
    return {
        "measured": True,
        "headways": len(heads),
        "meanHeadwayS": round(mean, 2),
        "vehPerHour": round(3600 / mean),
    }


def lamp_colour(roi_bgr: np.ndarray) -> str:
    """Colour of a lit signal lamp in a small ROI: RED / AMBER / GREEN, or DARK."""
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    lit = (hsv[..., 2] > 150) & (hsv[..., 1] > 90)
    h = hsv[..., 0][lit]
    if h.size < max(4, 0.02 * lit.size):
        return "DARK"
    n = {
        "RED": int(((h <= 8) | (h >= 170)).sum()),
        "AMBER": int(((h > 8) & (h <= 32)).sum()),
        "GREEN": int(((h >= 40) & (h <= 95)).sum()),
    }
    return max(n, key=n.get)


@dataclass
class TrackLog:
    classes: Counter = field(default_factory=Counter)
    zones: list[str] = field(default_factory=list)
    last: tuple[float, float] | None = None
    last_t: float = 0.0
    speed: float = 0.0  # pixels per second (1080p scale)
    stopped_before_line: bool = False
    crossed_at: float | None = None
    lines_crossed: set = field(default_factory=set)  # arms whose count line this track crossed


def load_profile(junction: str) -> dict:
    path = PROFILES / f"{junction}.json"
    if not path.exists():
        raise SystemExit(
            f"No camera profile {path}. Copy profiles/TEMPLATE.json and draw the zones on the first frame."
        )
    return json.loads(path.read_text())


def quality(frames: list[np.ndarray], fps: float) -> dict:
    grey = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
    sharp = float(np.median([cv2.Laplacian(g, cv2.CV_64F).var() for g in grey]))
    bright = float(np.median([g.mean() for g in grey]))
    warn = []
    if fps < MIN_FPS:
        warn.append(f"frame rate {fps:.0f} fps is below {MIN_FPS:.0f}")
    if sharp < MIN_SHARPNESS:
        warn.append("video looks blurred or out of focus")
    if bright < MIN_BRIGHTNESS:
        warn.append("video is too dark (night?)")
    return {
        "fps": round(fps, 1),
        "sharpness": round(sharp, 1),
        "brightness": round(bright, 1),
        "warnings": warn,
        "ok": not warn,
    }


def run(video: Path, junction: str, max_seconds: float | None = None, profile: dict | None = None,
        out_dir: Path | None = None, register: bool = True) -> dict:  # fmt: skip
    """Analyse one clip. `profile` / `out_dir` let the dashboard's video intake (intake.py) pass its own."""
    prof = profile or load_profile(junction)
    out = out_dir or OUT / junction
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    scale = 1920 / max(1, w)  # speeds in 1080p pixels, so thresholds do not depend on the resolution
    zones = {k: np.array(v["polygon"], np.int32) for k, v in prof["approaches"].items()}
    count_lines = {
        k: (tuple(v["count_line"][0]), tuple(v["count_line"][1]))
        for k, v in prof["approaches"].items()
        if v.get("count_line")
    }
    names_by_side = {k: v["name"] for k, v in prof["approaches"].items()}
    stop = prof.get("stop_line")
    lamp = prof.get("lamp_roi")
    cross = np.array(prof["crosswalk"], np.int32) if prof.get("crosswalk") else None
    start_clock = sum(
        int(x) * m for x, m in zip(prof.get("start_clock", "18:00").split(":"), (3600, 60), strict=True)
    )

    det, coco, blur = Detector("uvh"), Detector("coco"), Blurrer()
    names = class_names("uvh")
    # dense mixed traffic: keep lost tracks for 2 s and start tracks at lower confidence, so fewer IDs break
    tracker = sv.ByteTrack(
        track_activation_threshold=0.25,
        lost_track_buffer=round(2 * fps),
        minimum_matching_threshold=0.8,
        frame_rate=round(fps),
    )
    ptracker = sv.ByteTrack(frame_rate=max(1, round(fps / 5)))
    logs: dict[int, TrackLog] = defaultdict(TrackLog)
    people: dict[int, list[float]] = defaultdict(list)  # track id -> times inside the crosswalk
    queue_rows: list[dict] = []
    lamp_rows: list[tuple[float, str]] = []
    sample: list[np.ndarray] = []
    pw = 960
    ph = round(h * pw / w)
    writer = cv2.VideoWriter(str(out / "preview.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps / 2, (pw, ph))
    box_ann, lab_ann = sv.BoxAnnotator(thickness=2), sv.LabelAnnotator(text_scale=0.4, text_padding=2)
    persons = np.zeros((0, 4))
    k = 0
    while True:
        ok, frame = cap.read()
        if not ok or (max_seconds and k / fps > max_seconds):
            break
        t = k / fps
        if k % round(fps * 10) == 0:
            sample.append(frame)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        d = det(rgb, 0.3)
        sd = tracker.update_with_detections(
            sv.Detections(xyxy=d.boxes.astype(float), confidence=d.scores, class_id=d.labels)
        )
        for (x1, y1, x2, y2), tid, cid in zip(sd.xyxy, sd.tracker_id, sd.class_id, strict=True):
            lg = logs[int(tid)]
            p = ((x1 + x2) / 2, y2)  # bottom centre: where the vehicle touches the road
            lg.classes[names.get(int(cid), "Others")] += 1
            z = next((s for s, poly in zones.items() if cv2.pointPolygonTest(poly, p, False) >= 0), None)
            if z and (not lg.zones or lg.zones[-1] != z):
                lg.zones.append(z)
            if lg.last is not None:
                for side, (la, lb) in count_lines.items():
                    if side not in lg.lines_crossed and crosses(lg.last, p, la, lb):
                        lg.lines_crossed.add(side)
            if lg.last is not None and t > lg.last_t:
                v = math.dist(p, lg.last) * scale / (t - lg.last_t)
                lg.speed = 0.7 * lg.speed + 0.3 * v
                if stop and lg.crossed_at is None:
                    a, b = tuple(stop["line"][0]), tuple(stop["line"][1])
                    if crosses(lg.last, p, a, b):
                        lg.crossed_at = t
                    elif lg.speed < STOPPED_PX_S and z == stop["approach"]:
                        lg.stopped_before_line = True
            lg.last, lg.last_t = p, t
        if k % round(fps) == 0:  # once a second: queues and the lamp
            row = {"t_s": round(t), "clock": _clock(start_clock + t)}
            for s in zones:
                row[s] = sum(
                    1
                    for tid in sd.tracker_id
                    if logs[int(tid)].zones[-1:] == [s] and logs[int(tid)].speed < STOPPED_PX_S
                )
            queue_rows.append(row)
            if lamp:
                x, y, lw, lh = lamp
                lamp_rows.append((t, lamp_colour(frame[y : y + lh, x : x + lw])))
        if k % 5 == 0:  # people: every 5th frame is enough for walking speeds
            pd = coco(rgb, 0.4)
            keep = pd.labels == COCO_IDS["person"]
            pdet = ptracker.update_with_detections(
                sv.Detections(
                    xyxy=pd.boxes[keep].astype(float), confidence=pd.scores[keep], class_id=pd.labels[keep]
                )
            )
            persons = pdet.xyxy
            if cross is not None:
                for (x1, y1, x2, y2), tid in zip(pdet.xyxy, pdet.tracker_id, strict=True):
                    if cv2.pointPolygonTest(cross, ((x1 + x2) / 2, y2), False) >= 0:
                        people[int(tid)].append(t)
        if k % 2 == 0:  # preview at half frame rate, blurred BEFORE it is written
            shown = blur(frame, sd.xyxy, [names.get(int(c), "Others") for c in sd.class_id], persons)
            for s, poly in zones.items():
                cv2.polylines(shown, [poly], True, (0, 200, 255), 2)
                cv2.putText(shown, names_by_side[s], tuple(int(v) for v in poly[0]), 0, 0.6, (0, 200, 255), 2)
            if stop:
                cv2.line(shown, tuple(stop["line"][0]), tuple(stop["line"][1]), (60, 60, 255), 3)
            for la, lb in count_lines.values():
                cv2.line(shown, tuple(int(v) for v in la), tuple(int(v) for v in lb), (255, 200, 0), 2)
            labels = [
                f"#{tid} {names.get(int(c), '?')}" for tid, c in zip(sd.tracker_id, sd.class_id, strict=True)
            ]
            shown = lab_ann.annotate(box_ann.annotate(shown, sd), sd, labels)
            writer.write(cv2.resize(shown, (pw, ph)))
        k += 1
        if k % round(fps * 15) == 0:
            print(f"[cv-video] {t:.0f} s processed, {len(logs)} vehicles tracked", flush=True)
    writer.release()
    cap.release()
    return _write_outputs(
        prof,
        junction,
        out,
        video,
        logs,
        names_by_side,
        queue_rows,
        lamp_rows,
        people,
        start_clock,
        quality(sample, fps),
        k / fps,
        register,
    )


def _clock(s: float) -> str:
    s = int(s) % 86400
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def _write_outputs(
    prof,
    junction,
    out,
    video,
    logs,
    names_by_side,
    queue_rows,
    lamp_rows,
    people,
    start_clock,
    q,
    seconds,
    register=True,
) -> dict:
    # --- turning counts (tmc_clean.csv schema + source) ---
    moves: dict[tuple[str, str, int], Counter] = defaultdict(Counter)
    for lg in logs.values():
        if len(lg.zones) < 2 or lg.zones[0] == lg.zones[-1] or sum(lg.classes.values()) < 3:
            continue  # partial or stationary tracks are not counted
        cls = UVH_TO_SURVEY[lg.classes.most_common(1)[0][0]]
        moves[(lg.zones[0], lg.zones[-1], slot_of(start_clock + (lg.last_t or 0)))][cls] += 1
    pairs = sorted({(a, b) for a, b, _ in moves})
    rows = []
    for (a, b, slot), c in sorted(moves.items()):
        fast, slow = sum(c[x] for x in FAST), sum(c[x] for x in SLOW)
        rows.append({
            "junction_id": junction, "junction_name": prof.get("name", junction), "tmc_code": "", "survey_date": prof.get("date", ""),
            "day": "", "source_file": Path(video).name, "movement": pairs.index((a, b)) + 1, "from_approach": names_by_side[a],
            "to_approach": names_by_side[b], "turn": turn_of(a, b) or "", "slot": slot, "start": _clock(slot * 900 + 8 * 3600)[:5],
            **{x: c[x] for x in FAST}, "total_fast": fast, **{x: c[x] for x in SLOW}, "total_slow": slow, "total_veh": fast + slow,
            "total_pcu": round(sum(c[x] * PCU[x] for x in c), 1), "total_slow_reported": slow, "source": "FIELD",
        })  # fmt: skip
    cols = ["junction_id", "junction_name", "tmc_code", "survey_date", "day", "source_file", "movement", "from_approach",
            "to_approach", "turn", "slot", "start", *FAST, "total_fast", *SLOW, "total_slow", "total_veh", "total_pcu",
            "total_slow_reported", "source"]  # fmt: skip
    _csv(out / "counts.csv", cols, rows)
    # approach volumes: vehicles whose track crosses the arm's count line (each track counted once per line),
    # which stays reliable when tracks break in dense traffic; the movement split above uses linked tracks only
    entering: dict[str, Counter] = defaultdict(Counter)
    for lg in logs.values():
        for side in lg.lines_crossed:
            if lg.classes:
                entering[side][UVH_TO_SURVEY[lg.classes.most_common(1)[0][0]]] += 1
    vol_rows = [{"approach": names_by_side[a], "side": a, **{x: c[x] for x in FAST + SLOW}, "total_veh": sum(c.values()),
                 "total_pcu": round(sum(c[x] * PCU[x] for x in c), 1), "per_hour_veh": round(sum(c.values()) * 3600 / max(1, seconds)),
                 "source": "FIELD"} for a, c in sorted(entering.items())]  # fmt: skip
    _csv(
        out / "approach_volumes.csv",
        ["approach", "side", *FAST, *SLOW, "total_veh", "total_pcu", "per_hour_veh", "source"],
        vol_rows,
    )
    _csv(out / "queues.csv", ["t_s", "clock", *names_by_side], queue_rows)

    # --- saturation flow at the stop line ---
    sat: dict = {"measured": False, "reason": "no stop line in the camera profile"}
    stop = prof.get("stop_line")
    if stop:
        crossed = sorted((lg.crossed_at, lg.stopped_before_line, UVH_TO_SURVEY[lg.classes.most_common(1)[0][0]])
                         for lg in logs.values() if lg.crossed_at is not None and lg.classes)  # fmt: skip
        sat = saturation_from_headways([c[0] for c in crossed], [c[1] for c in crossed])
        mix = Counter(c[2] for c in crossed if c[1])
        pcu_per_veh = sum(PCU[k] * n for k, n in mix.items()) / max(1, sum(mix.values()))
        if sat["measured"]:
            sat["pcuPerHour"] = round(sat["vehPerHour"] * pcu_per_veh)
        sat |= {"approach": names_by_side.get(stop["approach"], stop["approach"]), "crossings": len(crossed),
                "queuedCrossings": sum(1 for c in crossed if c[1]), "classMix": dict(mix), "pcuPerVehicle": round(pcu_per_veh, 3),
                "method": "HCM discharge headways from the 5th queued vehicle (no lamp needed); per stop line, all lanes"}  # fmt: skip
    (out / "saturation.json").write_text(json.dumps(sat, indent=2))

    # --- signal state from the lamp ROI ---
    timings = {
        "measured": False,
        "reason": "no lamp ROI in the camera profile (the lamp must face the camera)",
    }
    if lamp_rows:
        _csv(
            out / "signal_states.csv",
            ["t_s", "colour"],
            [{"t_s": round(t), "colour": c} for t, c in lamp_rows],
        )
        runs: list[list] = []
        for t, c in lamp_rows:
            if runs and runs[-1][0] == c:
                runs[-1][2] = t
            else:
                runs.append([c, t, t])
        inner = runs[1:-1]  # the first and last runs are cut by the clip
        greens = [r[2] - r[1] + 1 for r in inner if r[0] == "GREEN"]
        ambers = [r[2] - r[1] + 1 for r in inner if r[0] == "AMBER"]
        starts = [r[1] for r in inner if r[0] == "GREEN"]
        cycles = [b - a for a, b in itertools.pairwise(starts)]
        if greens:
            timings = {"measured": True, "greenS": float(np.median(greens)), "amberS": float(np.median(ambers)) if ambers else None,
                       "cycleS": float(np.median(cycles)) if cycles else None, "cycles": len(greens)}  # fmt: skip
            _csv(out / "signal_timings_field.csv",
                 ["junction_id", "date", "time_window", "phase_no", "approaches_served", "green_s", "amber_s", "all_red_s", "cycle_s", "signal_mode", "notes"],
                 [{"junction_id": junction, "date": prof.get("date", ""), "time_window": f"{_clock(start_clock)[:5]}-{_clock(start_clock + seconds)[:5]}",
                   "phase_no": 1, "approaches_served": names_by_side.get(prof.get("lamp_approach", ""), ""), "green_s": round(timings["greenS"]),
                   "amber_s": round(timings["amberS"]) if timings["amberS"] else "", "all_red_s": "", "cycle_s": round(timings["cycleS"]) if timings["cycleS"] else "",
                   "signal_mode": "OBSERVED", "notes": f"FIELD: video lamp ROI, {len(greens)} cycles; REVIEW before copying into data/signal_timings.csv"}])  # fmt: skip

    # --- pedestrians ---
    ped = [
        {"track": tid, "crossing_s": round(ts[-1] - ts[0], 1)}
        for tid, ts in people.items()
        if ts[-1] - ts[0] >= 1.0
    ]
    _csv(out / "pedestrians.csv", ["track", "crossing_s"], ped)
    (out / "quality.json").write_text(json.dumps(q, indent=2))

    counted = sum(r["total_veh"] for r in rows)
    summary = {
        "junctionId": junction, "clip": Path(video).name, "seconds": round(seconds), "vehiclesTracked": len(logs),
        "counts": counted if q["ok"] else None, "movements": len(pairs),
        "approachVolumes": {r["approach"]: r["per_hour_veh"] for r in vol_rows} if q["ok"] else None, "saturation": sat if q["ok"] else {"measured": False, "reason": "quality"},
        "signal": timings, "pedestrianCrossings": len(ped), "quality": q,
        "source": "FIELD" if junction.startswith("J0") else "FIELD (demo clip, not a pilot junction)",
    }  # fmt: skip
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    if register:
        _register(summary)
    return summary


def _csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols)
        wr.writeheader()
        wr.writerows(rows)


def _register(summary: dict) -> None:
    """Add this clip's aggregate numbers (never frames) to reports/cv_eval.json for the dashboard."""
    path = REPORTS / "cv_eval.json"
    data = json.loads(path.read_text()) if path.exists() else {"name": "cv", "videos": []}
    vids = [
        v
        for v in data.get("videos", [])
        if not (v["junctionId"] == summary["junctionId"] and v["clip"] == summary["clip"])
    ]
    vids.append({k: summary[k] for k in ("junctionId", "clip", "seconds", "counts", "movements", "approachVolumes", "pedestrianCrossings", "source")}
                | {"saturationVehPerHour": summary["saturation"].get("vehPerHour"), "saturationPcuPerHour": summary["saturation"].get("pcuPerHour"),
                   "qualityOk": summary["quality"]["ok"]})  # fmt: skip
    data["videos"] = vids
    REPORTS.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("junction")
    ap.add_argument("--max-seconds", type=float)
    a = ap.parse_args()
    s = run(a.video, a.junction, a.max_seconds)
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
