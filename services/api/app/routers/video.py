"""Junction video intake (P8 W15): upload a clip, draw the camera profile on a privacy-blurred first
frame, run the CV pipeline (services/cv) and review the FIELD results. Operators only; the files stay
on this server. Raw videos are deleted after 30 days; only blurred previews and aggregates remain.

Upload "scan": allowed extension, size limit while streaming, container magic bytes, and OpenCV must
be able to decode frames (probe); anything else is deleted and rejected.
"""

import asyncio
import base64
import csv
import json
import logging
import re
import secrets
import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from .. import data_files as d
from ..audit_log import record
from ..auth import operator
from ..config import ROOT
from ..connectors.timing_import import COLUMNS as TIMING_COLUMNS
from ..db import connect
from ..tables import video_jobs

router = APIRouter(prefix="/video", tags=["video"])
log = logging.getLogger("haribatti.video")
UPLOADS = ROOT / "data/uploads/video"
CV_DIR = ROOT / "services/cv"
MAX_BYTES = 2 * 1024**3  # 2 GB
EXTS = {"mp4", "mov", "m4v", "avi", "mkv", "webm"}
OUTPUTS = {"counts.csv", "approach_volumes.csv", "queues.csv", "saturation.json", "signal_states.csv",
           "signal_timings_field.csv", "pedestrians.csv", "quality.json", "preview.mp4", "summary.json"}  # fmt: skip
PROPOSED = ROOT / "data/signal_timings.proposed.csv"
SIDES = ("N", "E", "S", "W")


def magic_ok(ext: str, head: bytes) -> bool:
    """Container signature matches the extension (mp4/mov: ftyp box, avi: RIFF, mkv/webm: EBML)."""
    if ext in ("mp4", "mov", "m4v"):
        return head[4:8] == b"ftyp"
    if ext == "avi":
        return head[:4] == b"RIFF" and head[8:12] == b"AVI "
    if ext in ("mkv", "webm"):
        return head[:4] == b"\x1a\x45\xdf\xa3"
    return False


def _job(job_id: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{16}", job_id):
        raise HTTPException(404, "No such upload")
    with connect() as c:
        row = c.execute(select(video_jobs).where(video_jobs.c.id == job_id)).first()
    if row is None:
        raise HTTPException(404, "No such upload")
    return dict(row._mapping)


def _set(job_id: str, **values) -> None:
    with connect() as c:
        c.execute(
            update(video_jobs).where(video_jobs.c.id == job_id).values(**values, updated_at=datetime.now(UTC))
        )


def _out(job: dict) -> dict:
    folder = UPLOADS / job["id"]
    return {"id": job["id"], "junctionId": job["junction_id"], "status": job["status"], "message": job["message"], "sizeBytes": job["size_bytes"],
            "probe": job["probe"], "profile": job["profile"], "summary": job["summary"], "uploadedBy": job["uploaded_by"],
            "createdAt": job["created_at"].isoformat(), "rawDeleted": not (UPLOADS / f"{job['id']}.{job['ext']}").exists(),
            "outputs": sorted(f.name for f in folder.iterdir() if f.name in OUTPUTS) if folder.is_dir() else [],
            "source": "FIELD (demo clip, not Jaipur)" if job["junction_id"] == "DEMO" else "FIELD"}  # fmt: skip


async def _cv(*args: str, model: bool) -> tuple[int, str]:
    uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
    cmd = [uv, "run", *(["--group", "model"] if model else []), "python", "-m", "hbcv.intake", *args]
    p = await asyncio.create_subprocess_exec(
        *cmd, cwd=CV_DIR, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    out, _ = await p.communicate()
    return p.returncode or 0, out.decode(errors="replace")[-2000:]


async def _probe(job_id: str, raw: Path) -> None:
    code, log_tail = await _cv("probe", str(raw), str(UPLOADS / job_id), model=True)
    info_path = UPLOADS / job_id / "probe.json"
    if code != 0 or not info_path.exists():
        raw.unlink(missing_ok=True)
        _set(job_id, status="rejected", message="Not a readable video (the file was deleted)")
        log.warning("video %s rejected: %s", job_id, log_tail[-300:])
        return
    info = json.loads(info_path.read_text())
    _set(
        job_id,
        status="ready",
        probe=info,
        message=None if info["quality"]["ok"] else "; ".join(info["quality"]["warnings"]),
    )


@router.post("/uploads", status_code=201)
async def upload(request: Request, junction: str = Query(pattern=r"^(J0[1-8]|DEMO)$"), filename: str = Query(max_length=200),
                 user: dict = Depends(operator)) -> dict:  # fmt: skip
    """Stream the raw file body to disk (no multipart), checking size and signature on the way."""
    # DEMO = a licensed clip from elsewhere, to try the tools: never counted as data for a Jaipur junction
    if junction != "DEMO" and junction not in {r["junction_id"] for r in d.registry()}:
        raise HTTPException(422, "Unknown junction")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in EXTS:
        raise HTTPException(415, f"Allowed video types: {', '.join(sorted(EXTS))}")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    job_id = secrets.token_hex(8)
    raw = UPLOADS / f"{job_id}.{ext}"  # generated name only: nothing from the client reaches the path
    size, head = 0, b""
    with raw.open("wb") as f:
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_BYTES:
                f.close()
                raw.unlink(missing_ok=True)
                raise HTTPException(413, "Video larger than 2 GB")
            if len(head) < 16:
                head += chunk[: 16 - len(head)]
            f.write(chunk)
    if size == 0 or not magic_ok(ext, head):
        raw.unlink(missing_ok=True)
        raise HTTPException(415, "The file content is not a video of the stated type")
    with connect() as c:
        c.execute(
            video_jobs.insert().values(
                id=job_id,
                junction_id=junction,
                ext=ext,
                size_bytes=min(size, 2**31 - 1),
                status="probing",
                uploaded_by=user["email"],
            )
        )
    record("video_upload", user["email"], user["role"], {"id": job_id, "junction": junction, "bytes": size})
    asyncio.create_task(_probe(job_id, raw))
    return {"id": job_id, "status": "probing"}


@router.get("/uploads")
def list_uploads(_user: dict = Depends(operator)) -> dict:
    with connect() as c:
        rows = c.execute(select(video_jobs).order_by(video_jobs.c.created_at.desc()).limit(100)).all()
    return {"uploads": [_out(dict(r._mapping)) for r in rows]}


@router.get("/uploads/{job_id}")
def get_upload(job_id: str, _user: dict = Depends(operator)) -> dict:
    return _out(_job(job_id))


@router.get("/uploads/{job_id}/frame")
def frame(job_id: str, _user: dict = Depends(operator)) -> dict:
    """The privacy-blurred first frame as a data URL, with the video's pixel size for drawing."""
    job = _job(job_id)
    f = UPLOADS / job_id / "frame.jpg"
    if not f.exists():
        raise HTTPException(409, "The frame is not ready yet")
    return {
        "image": "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode(),
        "width": job["probe"]["width"],
        "height": job["probe"]["height"],
    }


Point = list[float]


class Approach(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    polygon: list[Point] = Field(min_length=3, max_length=40)
    count_line: list[Point] | None = None


class StopLine(BaseModel):
    approach: str
    line: list[Point] = Field(min_length=2, max_length=2)


class Profile(BaseModel):
    name: str = Field(default="", max_length=120)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_clock: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    approaches: dict[str, Approach]
    stop_line: StopLine | None = None
    lamp_roi: list[int] | None = Field(default=None, min_length=4, max_length=4)
    lamp_approach: str | None = None
    crosswalk: list[Point] | None = None


def validate_profile(p: Profile, width: int, height: int, junction: str) -> list[str]:
    errs = []
    if not p.approaches or any(k not in SIDES for k in p.approaches):
        errs.append("approaches must be keyed N, E, S or W")
    known = {r["junction_id"]: r for r in d.registry()}.get(junction)
    names = {
        n.strip() for n in (known or {}).get("approaches_used", "").split("|") if n.strip()
    }  # DEMO: any names
    for k, a in p.approaches.items():
        if names and a.name not in names:
            errs.append(f"{k}: '{a.name}' is not an approach of {junction} ({', '.join(sorted(names))})")
    pts = [pt for a in p.approaches.values() for pt in a.polygon + (a.count_line or [])]
    pts += (p.stop_line.line if p.stop_line else []) + (p.crosswalk or [])
    if any(len(pt) != 2 or not (0 <= pt[0] <= width and 0 <= pt[1] <= height) for pt in pts):
        errs.append(f"every point must be inside the {width}x{height} frame")
    if p.stop_line and p.stop_line.approach not in p.approaches:
        errs.append("the stop line must belong to one of the approaches")
    if p.lamp_roi:
        x, y, w, h = p.lamp_roi
        if w < 4 or h < 4 or x < 0 or y < 0 or x + w > width or y + h > height:
            errs.append("the lamp box must be inside the frame and at least 4x4 px")
        if p.lamp_approach not in p.approaches:
            errs.append("say which approach the lamp controls")
    return errs


def _ints(v):
    """Pixel coordinates as whole numbers (OpenCV drawing needs ints)."""
    if isinstance(v, float):
        return round(v)
    if isinstance(v, list):
        return [_ints(x) for x in v]
    if isinstance(v, dict):
        return {k: _ints(x) for k, x in v.items()}
    return v


@router.patch("/uploads/{job_id}/profile")
def save_profile(job_id: str, body: Profile, user: dict = Depends(operator)) -> dict:
    job = _job(job_id)
    if job["status"] not in ("ready", "done", "failed"):
        raise HTTPException(409, f"The upload is {job['status']}")
    if errs := validate_profile(body, job["probe"]["width"], job["probe"]["height"], job["junction_id"]):
        raise HTTPException(422, {"errors": errs})
    prof = {**_ints(body.model_dump(exclude_none=True)), "junction": job["junction_id"]}
    (UPLOADS / job_id / "profile.json").write_text(json.dumps(prof, indent=2) + "\n")
    _set(job_id, profile=prof)
    record("video_profile", user["email"], user["role"], {"id": job_id})
    return _out(_job(job_id))


class Analyse(BaseModel):
    maxSeconds: float | None = Field(default=None, gt=0, le=4 * 3600)


async def _analyse(job_id: str, raw: Path, max_s: float | None) -> None:
    args = ["analyse", str(raw), str(UPLOADS / job_id / "profile.json"), str(UPLOADS / job_id)]
    code, tail = await _cv(*args, *(["--max-seconds", str(max_s)] if max_s else []), model=True)
    sp = UPLOADS / job_id / "summary.json"
    if code != 0 or not sp.exists():
        _set(
            job_id,
            status="failed",
            message="Analysis failed: " + tail.strip().splitlines()[-1][:300]
            if tail.strip()
            else "Analysis failed",
        )
        return
    s = json.loads(sp.read_text())
    _set(
        job_id,
        status="done",
        summary=s,
        message=None if s.get("quality", {}).get("ok", True) else "Quality too low: numbers withheld",
    )


@router.post("/uploads/{job_id}/analyse", status_code=202)
async def analyse(job_id: str, body: Analyse, user: dict = Depends(operator)) -> dict:
    job = _job(job_id)
    raw = UPLOADS / f"{job_id}.{job['ext']}"
    if job["status"] not in ("ready", "done", "failed") or not job["profile"]:
        raise HTTPException(409, "Save a camera profile first")
    if not raw.exists():
        raise HTTPException(410, "The raw video was deleted after 30 days; upload it again")
    _set(job_id, status="analysing", message=None)
    record("video_analyse", user["email"], user["role"], {"id": job_id})
    asyncio.create_task(_analyse(job_id, raw, body.maxSeconds))
    return {"id": job_id, "status": "analysing"}


@router.get("/uploads/{job_id}/outputs/{name}")
def output(job_id: str, name: str, _user: dict = Depends(operator)) -> FileResponse:
    _job(job_id)
    if name not in OUTPUTS:
        raise HTTPException(404, "No such output")
    f = UPLOADS / job_id / name
    if not f.exists():
        raise HTTPException(404, "Not produced for this clip")
    return FileResponse(f, filename=f"{job_id}-{name}")


@router.post("/uploads/{job_id}/timings-proposal", status_code=201)
def propose_timings(job_id: str, user: dict = Depends(operator)) -> dict:
    """Append the measured green/amber durations to data/signal_timings.proposed.csv for a person to review.
    Nothing is written to data/signal_timings.csv (the source of truth) automatically."""
    job = _job(job_id)
    if job["junction_id"] == "DEMO":
        raise HTTPException(409, "A demo clip is not a Jaipur junction: its timings are never proposed")
    f = UPLOADS / job_id / "signal_timings_field.csv"
    if job["status"] != "done" or not f.exists():
        raise HTTPException(409, "No measured timings for this clip (does the profile have a lamp box?)")
    if job["summary"] and not job["summary"].get("quality", {}).get("ok", True):
        raise HTTPException(409, "The video quality was too low: timings are not proposed")
    with f.open(newline="", encoding="utf-8") as fh:
        rows = [{k: r.get(k, "") for k in TIMING_COLUMNS} for r in csv.DictReader(fh)]
    for r in rows:
        r["notes"] = f"FIELD video {job_id} – REVIEW; {r.get('notes', '')}".strip("; ")
    new = not PROPOSED.exists()
    with PROPOSED.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=TIMING_COLUMNS)
        if new:
            w.writeheader()
        w.writerows(rows)
    record("video_timings_proposed", user["email"], user["role"], {"id": job_id, "rows": len(rows)})
    return {
        "rows": len(rows),
        "file": "data/signal_timings.proposed.csv",
        "note": "Review, then copy trusted rows into data/signal_timings.csv.",
    }
