"""Download everything W4 needs, once, into gitignored folders (services/cv/vendor, weights, data).

- RT-DETR code (lyuwenyu/RT-DETR, Apache-2.0): shallow git clone, commit recorded.
- OpenCV Zoo YuNet face detector (MIT) for the privacy blur.
- IISc UVH-26 RT-DETRv2-S weights + config (Apache-2.0) and the COCO RT-DETRv2-S baseline (Apache-2.0).
- UVH-26 validation annotations (CC BY 4.0) and a seeded random sample of validation images.
Images are 1080p PNGs of about 3.3 MB each, so the sample is kept small enough that the whole
download stays under the 2 GB budget approved for W4; the script refuses to go over it.
Only GET requests: nothing from this project is sent anywhere.
Run: uv run python -m hbcv.fetch [--images 400]
"""

import argparse
import json
import random
import shutil
import subprocess
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .paths import COCO_MODEL, FACE_MODEL, UVH_CONFIG, UVH_MODEL, VAL_DIR, VENDOR, WEIGHTS

BUDGET_BYTES = 2_000_000_000
HF_MODEL = "https://huggingface.co/iisc-aim/UVH-26/resolve/main/"
HF_DATA = "https://huggingface.co/datasets/iisc-aim/UVH-26/resolve/main/"
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
COCO_URL = (
    "https://github.com/lyuwenyu/storage/releases/download/v0.2/rtdetrv2_r18vd_120e_coco_rerun_48.1.pth"
)
SEED = 26


class Budget:
    def __init__(self, limit: int) -> None:
        self.limit, self.used = limit, 0
        self.lock = threading.Lock()

    def get(self, url: str, dest: Path) -> int:
        """Download url to dest unless it is already there. Returns bytes downloaded now."""
        if dest.exists() and dest.stat().st_size > 0:
            return 0
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "haribatti-cv"})) as r:
            size = int(r.headers.get("Content-Length") or 0)
            with self.lock:  # reserve the bytes before downloading, so parallel downloads cannot overshoot
                if self.used + size > self.limit:
                    raise SystemExit(
                        f"Refusing {url}: would pass the {self.limit / 1e9:.1f} GB download budget"
                    )
                self.used += size
            with tmp.open("wb") as f:
                shutil.copyfileobj(r, f, length=1 << 20)
        tmp.rename(dest)
        return dest.stat().st_size


def image_paths() -> dict[str, str]:
    """file name -> repo path for every validation image (the tree API pages 1,000 entries at a time)."""
    import re

    out: dict[str, str] = {}
    url = "https://huggingface.co/api/datasets/iisc-aim/UVH-26/tree/main/UVH-26-Val/data?recursive=true"
    while url:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "haribatti-cv"})) as r:
            for f in json.loads(r.read()):
                if f["type"] == "file":
                    out[Path(f["path"]).name] = f["path"]
            m = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("Link") or "")
            url = m.group(1) if m else ""
    return out


def clone_rtdetr() -> str:
    if not VENDOR.exists():
        VENDOR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", "https://github.com/lyuwenyu/RT-DETR.git", str(VENDOR)],
            check=True,
        )
    return subprocess.run(
        ["git", "-C", str(VENDOR), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", type=int, default=400, help="validation images to sample (about 3.3 MB each)")
    a = ap.parse_args()
    b = Budget(BUDGET_BYTES)
    # the budget covers everything W4 downloads, including files fetched by earlier runs
    b.used = sum(
        f.stat().st_size for d in (WEIGHTS, VAL_DIR) if d.exists() for f in d.rglob("*") if f.is_file()
    )
    commit = clone_rtdetr()
    b.get(HF_MODEL + "weights/RT-DETRv2-S/UVH-26-MV-RT-DETRv2-S.pth", UVH_MODEL)
    b.get(HF_MODEL + "configs/rtdetrv2_s.yaml", UVH_CONFIG)
    b.get(HF_MODEL + "uvh_classes.txt", WEIGHTS / "uvh_classes.txt")
    b.get(COCO_URL, COCO_MODEL)
    b.get(YUNET_URL, FACE_MODEL)  # face detector for the privacy blur (MIT)
    ann = VAL_DIR / "UVH-26-MV-Val.json"
    b.get(HF_DATA + "UVH-26-Val/UVH-26-MV-Val.json", ann)
    coco = json.loads(ann.read_text())
    images = sorted(coco["images"], key=lambda im: im["id"])
    sample = random.Random(SEED).sample(images, min(a.images, len(images)))
    where = image_paths() if sample else {}

    def one(im: dict) -> None:
        name = Path(im["file_name"]).name
        b.get(HF_DATA + where[name], VAL_DIR / "images" / name)

    with ThreadPoolExecutor(8) as pool:  # 8 downloads at a time
        for k, _ in enumerate(pool.map(one, sample), 1):
            if k % 50 == 0:
                print(f"[fetch] {k}/{len(sample)} images, {b.used / 1e9:.2f} GB in total", flush=True)
    manifest = {
        "rtdetr_commit": commit,
        "sample_seed": SEED,
        "sample_image_ids": [im["id"] for im in sample],
        "val_images_total": len(images),
        "total_download_bytes": b.used,
    }
    (VAL_DIR / "sample.json").write_text(json.dumps(manifest, indent=1))
    print(f"[fetch] done: {len(sample)} images; {b.used / 1e9:.2f} GB in total; RT-DETR {commit[:10]}")


if __name__ == "__main__":
    main()
