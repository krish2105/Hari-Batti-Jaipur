"""mAP evaluation on a seeded sample of the UVH-26 validation split -> reports/cv_eval.json.

1. IISc RT-DETRv2-S (UVH-26 weights) on all 14 Indian vehicle classes: mAP50:95, mAP50, per class.
2. The same model vs the COCO-trained RT-DETRv2-S on the classes both know: car (Hatchback, Sedan,
   SUV, MUV, Van), bus (Bus, Mini-bus), truck (Truck, LCV), motorcycle (Two-wheeler), bicycle.
   Ground-truth boxes of the other classes (Three-wheeler, Tempo-traveller, Others) are marked as
   "ignore" (COCO iscrowd), so neither model is punished for boxes the COCO taxonomy cannot name.
The UVH-26 validation split was not used to fit the IISc weights (it may have guided their model
selection, so these scores are validation scores, not a sealed test set).
Run: uv run python -m hbcv.evaluate
"""

import contextlib
import io
import json
import time

import numpy as np
from PIL import Image
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

from .detector import COCO_IDS, Detector, class_names
from .paths import REPORTS, VAL_DIR

COMMON = {"car": 1, "bus": 2, "truck": 3, "motorcycle": 4, "bicycle": 5}
UVH_TO_COMMON = {
    "Hatchback": "car", "Sedan": "car", "SUV": "car", "MUV": "car", "Van": "car", "Bus": "bus", "Mini-bus": "bus",
    "Truck": "truck", "LCV": "truck", "Two-wheeler": "motorcycle", "Bicycle": "bicycle",
}  # fmt: skip
COCO_TO_COMMON = {COCO_IDS[k]: k for k in COMMON}
MIN_SCORE = 0.01  # keep low-confidence boxes: mAP integrates over the whole precision-recall curve


def _coco_eval(gt: dict, dets: list[dict], per_class: bool = False) -> dict:
    """pycocotools bbox evaluation (quietly). Returns mAP50:95, mAP50 and optional per-class AP."""
    with contextlib.redirect_stdout(io.StringIO()):
        g = COCO()
        g.dataset = gt
        g.createIndex()
        d = g.loadRes(dets) if dets else COCO()
        e = COCOeval(g, d, "bbox")
        e.evaluate()
        e.accumulate()
        e.summarize()
    out = {"map50_95": round(float(e.stats[0]), 4), "map50": round(float(e.stats[1]), 4)}
    if per_class:
        prec = e.eval["precision"]  # [iou, recall, class, area, maxdets]
        out["classes"] = {}
        for k, cid in enumerate(e.params.catIds):
            p = prec[:, :, k, 0, -1]
            out["classes"][cid] = round(float(p[p > -1].mean()), 4) if (p > -1).any() else None
    return out


def _dets(det: Detector, images: list[dict], mapping) -> tuple[list[dict], float]:
    """Run a detector on every sample image; mapping(label) -> category id or None (dropped)."""
    out: list[dict] = []
    t = 0.0
    for im in images:
        pil = Image.open(VAL_DIR / "images" / im["file_name"]).convert("RGB")
        t0 = time.perf_counter()
        r = det(pil, MIN_SCORE)
        t += time.perf_counter() - t0
        for (x1, y1, x2, y2), lab, s in zip(r.boxes, r.labels, r.scores, strict=True):
            cid = mapping(int(lab))
            if cid is not None:
                out.append(
                    {
                        "image_id": im["id"],
                        "category_id": cid,
                        "bbox": [float(x1), float(y1), float(x2 - x1), float(y2 - y1)],
                        "score": float(s),
                    }
                )
    return out, 1000 * t / max(1, len(images))


def main() -> None:
    full = json.loads((VAL_DIR / "UVH-26-MV-Val.json").read_text())
    have = {p.name for p in (VAL_DIR / "images").glob("*.png")}
    images = [im for im in full["images"] if im["file_name"] in have]
    ids = {im["id"] for im in images}
    anns = [a for a in full["annotations"] if a["image_id"] in ids]
    cats = {c["id"]: c["name"] for c in full["categories"]}
    gt14 = {"images": images, "annotations": anns, "categories": full["categories"]}
    # common-class ground truth: other classes become "ignore" regions
    common_anns = []
    for a in anns:
        c = UVH_TO_COMMON.get(cats[a["category_id"]])
        b = {**a, "category_id": COMMON[c] if c else COMMON["car"], "iscrowd": 0 if c else 1}
        common_anns.append(b)
    gt5 = {
        "images": images,
        "annotations": common_anns,
        "categories": [{"id": v, "name": k} for k, v in COMMON.items()],
    }
    print(f"[cv-eval] {len(images)} images, {len(anns):,} boxes", flush=True)

    uvh = Detector("uvh")
    names = class_names("uvh")
    d14, ms_uvh = _dets(uvh, images, lambda lab: lab if lab in cats else None)
    r14 = _coco_eval(gt14, d14, per_class=True)
    d5u = [
        {**d, "category_id": COMMON[UVH_TO_COMMON[names[d["category_id"]]]]}
        for d in d14
        if names.get(d["category_id"]) in UVH_TO_COMMON
    ]
    r5u = _coco_eval(gt5, d5u)
    del uvh
    coco = Detector("coco")
    d5c, ms_coco = _dets(coco, images, lambda lab: COMMON.get(COCO_TO_COMMON.get(lab, ""), None))
    r5c = _coco_eval(gt5, d5c)

    n_per = {cid: sum(a["category_id"] == cid for a in anns) for cid in cats}
    result = {
        "name": "cv",
        "dataset": "UVH-26 validation split (IISc, CC BY 4.0), seeded random sample",
        "images": len(images),
        "boxes": len(anns),
        "device": f"Apple silicon GPU (MPS), {ms_uvh:.0f} ms per 1080p image (RT-DETRv2-S, 640 px input)",
        "models": [
            {"id": "uvh-14", "label": "RT-DETRv2-S, IISc UVH-26 weights · 14 Indian classes", **r14, "licence": "Apache-2.0"},
            {"id": "uvh-common", "label": "RT-DETRv2-S, IISc UVH-26 weights · 5 common classes", **r5u, "licence": "Apache-2.0"},
            {"id": "coco-common", "label": "RT-DETRv2-S, COCO weights (baseline) · 5 common classes", **r5c, "licence": "Apache-2.0"},
        ],
        "classes": [{"name": cats[c], "ap50_95": r14["classes"].get(c), "n": n_per[c]} for c in sorted(cats) if n_per[c] > 0],
        "speedMs": {"uvh": round(ms_uvh, 1), "coco": round(ms_coco, 1)},
        "pipeline": {
            "privacy": "Faces (YuNet) and number-plate zones blurred before any frame is saved; no ANPR, no identity tracking",
            "tracking": "ByteTrack (supervision, MIT)",
            "outputs": "turning counts (tmc_clean.csv schema, source FIELD), queue per approach per second, saturation flow, signal state from a lamp ROI",
        },
        "videos": [],
        "note": "Common classes: car = Hatchback+Sedan+SUV+MUV+Van, bus = Bus+Mini-bus, truck = Truck+LCV, "
        "motorcycle = Two-wheeler; Three-wheeler, Tempo-traveller and Others are ignore regions. "
        "Evaluated with pycocotools on the UVH-26 validation split (not used to fit the weights; it may have guided "
        "IISc's model selection, so treat these as validation scores).",
    }  # fmt: skip
    for m in result["models"]:
        m.pop("classes", None)
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / "cv_eval.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    result["videos"] = old.get("videos", [])  # keep results written by `make cv-video`
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({m["id"]: (m["map50_95"], m["map50"]) for m in result["models"]}), flush=True)


if __name__ == "__main__":
    np.set_printoptions(precision=3)
    main()
