"""Junction video intake for the dashboard (P8 W15).

    uv run python -m hbcv.intake probe VIDEO OUTDIR       -> OUTDIR/frame.jpg (privacy-blurred) + probe.json
    uv run --group model python -m hbcv.intake analyse VIDEO PROFILE.json OUTDIR [--max-seconds N]

probe: checks the file really is a video OpenCV can decode (the upload "scan"), measures frame rate,
size and length, runs the quality checks on frames spread over the clip, and saves the first frame
for the guided setup. That frame is made safe before it is saved: downscaled to at most 960 px wide,
faces pixelated (YuNet), vehicle number-plate zones pixelated when the detector is installed, and a
light blur so no plate stays readable.
analyse: runs video.run() with the camera profile drawn on the dashboard; outputs are source FIELD and
the numbers are withheld when the quality checks fail.
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from .privacy import Blurrer, pixelate
from .video import quality, run

MAX_W = 960


def _plate_zones(frame: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Lower part of every detected vehicle (where plates are), when the detector is installed."""
    try:
        from .detector import Detector

        d = Detector("uvh")(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), 0.3)
    except Exception:  # noqa: BLE001 - no model group: faces + downscale + blur still apply
        return []
    out = []
    for x1, y1, x2, y2 in np.asarray(d.boxes).reshape(-1, 4):
        top = int(y1 + 0.55 * (y2 - y1))
        out.append((int(x1), top, int(x2), int(y2)))
    return out


def safe_frame(frame: np.ndarray) -> np.ndarray:
    blur = Blurrer()
    out = frame.copy()
    for r in blur.faces(frame) + _plate_zones(frame):
        pixelate(out, r)
    h, w = out.shape[:2]
    if w > MAX_W:
        out = cv2.resize(out, (MAX_W, round(h * MAX_W / w)), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(out, (3, 3), 0)


def probe(video: Path, out_dir: Path) -> dict:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return {"ok": False, "reason": "not a video OpenCV can read"}
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    ok, first = cap.read()
    if not ok or first is None or w < 160 or h < 120:
        return {"ok": False, "reason": "no readable frames"}
    samples = [first]
    for k in range(1, 12):
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, k * n // 12))
        ok, f = cap.read()
        if ok:
            samples.append(f)
    cap.release()
    out_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / "frame.jpg"), safe_frame(first), [cv2.IMWRITE_JPEG_QUALITY, 80])
    info = {"ok": True, "fps": round(fps, 2), "width": w, "height": h, "frames": n,
            "seconds": round(n / fps, 1) if fps else None, "quality": quality(samples, fps or 0.0)}  # fmt: skip
    (out_dir / "probe.json").write_text(json.dumps(info, indent=2) + "\n")
    return info


def _ints(v):
    """Whole-pixel coordinates (OpenCV drawing refuses floats)."""
    if isinstance(v, float):
        return round(v)
    if isinstance(v, list):
        return [_ints(x) for x in v]
    if isinstance(v, dict):
        return {k: _ints(x) for k, x in v.items()}
    return v


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe")
    p.add_argument("video", type=Path)
    p.add_argument("out", type=Path)
    a2 = sub.add_parser("analyse")
    a2.add_argument("video", type=Path)
    a2.add_argument("profile", type=Path)
    a2.add_argument("out", type=Path)
    a2.add_argument("--max-seconds", type=float)
    a = ap.parse_args()
    if a.cmd == "probe":
        info = probe(a.video, a.out)
        print(json.dumps(info))
        sys.exit(0 if info["ok"] else 2)
    prof = _ints(json.loads(a.profile.read_text()))
    summary = run(
        a.video, prof.get("junction", "UPLOAD"), a.max_seconds, profile=prof, out_dir=a.out, register=False
    )
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps({"ok": True, "counts": summary.get("counts"), "qualityOk": summary["quality"]["ok"]}))


if __name__ == "__main__":
    main()
