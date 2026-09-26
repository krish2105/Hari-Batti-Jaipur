"""RT-DETRv2-S detectors (Apache-2.0 code from lyuwenyu/RT-DETR, cloned by fetch.py).

"uvh"  IISc UVH-26 weights: 14 Indian vehicle classes (label = UVH category id 1-14) (Hatchback ... Others), trained on Bengaluru CCTV.
"coco" the COCO-trained RT-DETRv2-S baseline (80 classes, includes person for pedestrian counts).
Both use the stock r18vd architecture; the IISc checkpoint is loaded strictly, so a mismatch fails loudly.
Runs on Apple silicon (MPS) when available, else CPU.
"""

import sys
from dataclasses import dataclass

import numpy as np
from PIL import Image

from .paths import COCO_MODEL, RTDETR_SRC, UVH_MODEL, WEIGHTS

STOCK_R18 = RTDETR_SRC / "configs" / "rtdetrv2" / "rtdetrv2_r18vd_120e_coco.yml"
UVH_CLASSES = [
    "Hatchback",
    "Sedan",
    "SUV",
    "MUV",
    "Bus",
    "Truck",
    "Three-wheeler",
    "Two-wheeler",
    "LCV",
    "Mini-bus",
    "Tempo-traveller",
    "Bicycle",
    "Van",
    "Others",
]  # fmt: skip  -- category ids 1..14 in the UVH-26 COCO files
# deploy mode returns contiguous 0-79 COCO indices (no remap to COCO ids)
COCO_IDS = {"person": 0, "bicycle": 1, "car": 2, "motorcycle": 3, "bus": 5, "truck": 7}


def device() -> str:
    import torch  # PyTorch is imported only when a model is used (the "model" dependency group)

    return "mps" if torch.backends.mps.is_available() else "cpu"


@dataclass
class Detections:
    boxes: np.ndarray  # (n, 4) x1, y1, x2, y2 in image pixels
    labels: np.ndarray  # (n,) category ids (UVH 1-14, or COCO ids)
    scores: np.ndarray  # (n,)


class Detector:
    """One RT-DETRv2-S model in deploy mode: image in, boxes/labels/scores out."""

    def __init__(self, kind: str = "uvh", dev: str | None = None) -> None:
        import torch

        if str(RTDETR_SRC) not in sys.path:
            sys.path.insert(0, str(RTDETR_SRC))
        from src.core import YAMLConfig  # the RT-DETR repo's own config system

        self.kind = kind
        self.dev = dev or device()
        over = {"PResNet": {"pretrained": False}}  # weights come from the checkpoint, no backbone download
        if kind == "uvh":
            over |= {"num_classes": 15, "remap_mscoco_category": False}  # ids 1-14 (0 unused)
            ckpt = UVH_MODEL
        else:
            ckpt = COCO_MODEL
        cfg = YAMLConfig(str(STOCK_R18), **over)
        state = torch.load(ckpt, map_location="cpu", weights_only=False)
        state = state["ema"]["module"] if "ema" in state else state["model"]
        cfg.model.load_state_dict(state, strict=True)
        self.model = cfg.model.deploy().to(self.dev).eval()
        self.post = cfg.postprocessor.deploy().to(self.dev).eval()

    def __call__(self, image: Image.Image | np.ndarray, min_score: float = 0.0) -> Detections:
        """Detect on one RGB image (PIL or HxWx3 uint8)."""
        import torch
        import torchvision.transforms.functional as TF

        with torch.no_grad():
            return self._detect(image, min_score, torch, TF)

    def _detect(self, image, min_score, torch, TF) -> Detections:
        im = Image.fromarray(image) if isinstance(image, np.ndarray) else image.convert("RGB")
        w, h = im.size
        x = TF.to_tensor(im.resize((640, 640))).unsqueeze(0).to(self.dev)
        size = torch.tensor([[w, h]], device=self.dev)
        labels, boxes, scores = self.post(self.model(x), size)
        keep = scores[0] >= min_score
        return Detections(
            boxes[0][keep].cpu().numpy(),
            labels[0][keep].cpu().numpy().astype(int),
            scores[0][keep].cpu().numpy(),
        )


def class_names(kind: str) -> dict[int, str]:
    if kind == "uvh":
        names = (
            (WEIGHTS / "uvh_classes.txt").read_text().splitlines()
            if (WEIGHTS / "uvh_classes.txt").exists()
            else UVH_CLASSES
        )
        return {i + 1: n for i, n in enumerate(names)}
    return {v: k for k, v in COCO_IDS.items()}
