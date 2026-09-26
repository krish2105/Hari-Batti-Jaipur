"""Write reports/cv_eval.md (human-readable) from reports/cv_eval.json. Run: uv run python -m hbcv.report"""

import json

from .paths import REPORTS


def _ap(v: float | None) -> str:
    return "—" if v is None else f"{v:.3f}"


def build(d: dict) -> str:
    L = [
        "# HariBatti — computer vision evaluation (W4)",
        "",
        f"> {d['dataset']}: {d['images']} images, {d['boxes']:,} labelled vehicles · {d['device']}",
        "",
        "## Detection accuracy (MODEL, validation data)",
        "",
        "| Model | mAP50:95 | mAP50 | Licence |",
        "| --- | --- | --- | --- |",
        *[f"| {m['label']} | {m['map50_95']:.3f} | {m['map50']:.3f} | {m['licence']} |" for m in d["models"]],
        "",
        d["note"],
        "",
        "## Per class (IISc UVH-26 weights, 14 classes)",
        "",
        "| Class | AP50:95 | Boxes in sample |",
        "| --- | --- | --- |",
        *[f"| {c['name']} | {_ap(c['ap50_95'])} | {c['n']:,} |" for c in d["classes"]],
        "",
        "## Pipeline",
        "",
        *[f"- **{k}**: {v}" for k, v in d["pipeline"].items()],
        "",
    ]
    if d.get("videos"):
        L += [
            "## Video runs (aggregates only; frames are never published)",
            "",
            "| Clip | Seconds | Linked movements | Arm volumes (veh/h, both directions) | Pedestrian crossings | Source |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for v in d["videos"]:
            vols = ", ".join(f"{k} {n:,}" for k, n in (v.get("approachVolumes") or {}).items())
            L.append(
                f"| {v['clip']} | {v['seconds']} | {v['counts']} | {vols} | {v['pedestrianCrossings']} | {v['source']} |"
            )
        L += ["", ("The demo clip shows Link Road, Cuttack (Wikimedia Commons, CC BY-SA 3.0, Subhashish Panigrahi): a demo of "
              "tracking and counting, not a pilot junction. Its signal lamps face away from the camera, so signal state and "
              "saturation flow are reported as not measured. Your own clip: `make cv-video VIDEO=clip.mp4 JUNCTION=J05`."), ""]  # fmt: skip
    return "\n".join(L)


def main() -> None:
    d = json.loads((REPORTS / "cv_eval.json").read_text())
    (REPORTS / "cv_eval.md").write_text(build(d))
    print("wrote reports/cv_eval.md")


if __name__ == "__main__":
    main()
