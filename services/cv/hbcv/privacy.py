"""Privacy first: faces and number-plate zones are pixelated BEFORE any frame is written to disk.

We blur zones, not only detections, so a missed face or plate is still covered:
- the lower band of every motor vehicle (where front and rear plates are mounted),
- the head zone of every two-wheeler, three-wheeler and bicycle (riders and passengers),
- the head zone of every detected person,
- any face the YuNet face detector (OpenCV Zoo, MIT) finds.
This over-blurs by design. There is no ANPR and no identity tracking anywhere in HariBatti.
"""

import cv2
import numpy as np

from .paths import FACE_MODEL

RIDDEN = {"Two-wheeler", "Three-wheeler", "Bicycle"}
NO_PLATE = {"Bicycle"}
PLATE_BAND = 0.38  # bottom share of a vehicle box that is pixelated
HEAD_BAND = 0.40  # top share of a ridden vehicle's box
PERSON_HEAD = 0.28  # top share of a person's box


def zones(
    boxes: np.ndarray, names: list[str], persons: np.ndarray | None = None
) -> list[tuple[int, int, int, int]]:
    """Rectangles (x1, y1, x2, y2) to pixelate for these detections (pure, unit-tested)."""
    out = []
    for (x1, y1, x2, y2), name in zip(boxes, names, strict=True):
        w, h = x2 - x1, y2 - y1
        if name not in NO_PLATE:
            out.append((x1 + 0.05 * w, y2 - PLATE_BAND * h, x2 - 0.05 * w, y2))
        if name in RIDDEN:
            out.append((x1, y1, x2, y1 + HEAD_BAND * h))
    for x1, y1, x2, y2 in persons if persons is not None else []:
        out.append((x1, y1, x2, y1 + PERSON_HEAD * (y2 - y1)))
    return [(int(a), int(b), int(c), int(d)) for a, b, c, d in out]


def pixelate(frame: np.ndarray, rect: tuple[int, int, int, int], block: int = 10) -> None:
    """Coarse mosaic in place (cannot be undone the way a light blur sometimes can)."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = max(0, rect[0]), max(0, rect[1]), min(w, rect[2]), min(h, rect[3])
    if x2 - x1 < 2 or y2 - y1 < 2:
        return
    roi = frame[y1:y2, x1:x2]
    small = cv2.resize(
        roi, (max(1, (x2 - x1) // block), max(1, (y2 - y1) // block)), interpolation=cv2.INTER_LINEAR
    )
    frame[y1:y2, x1:x2] = cv2.resize(small, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)


class Blurrer:
    """Applies every privacy zone plus detected faces to a BGR frame (returns a new frame)."""

    def __init__(self) -> None:
        self.face = None
        if FACE_MODEL.exists():
            self.face = cv2.FaceDetectorYN.create(str(FACE_MODEL), "", (320, 320), 0.6, 0.3, 5000)

    def faces(self, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        if self.face is None:
            return []
        h, w = frame.shape[:2]
        self.face.setInputSize((w, h))
        _, found = self.face.detect(frame)
        out = []
        for f in found if found is not None else []:
            x, y, fw, fh = f[:4]
            pad = 0.25
            out.append(
                (int(x - pad * fw), int(y - pad * fh), int(x + (1 + pad) * fw), int(y + (1 + pad) * fh))
            )
        return out

    def __call__(
        self, frame: np.ndarray, boxes: np.ndarray, names: list[str], persons: np.ndarray | None = None
    ) -> np.ndarray:
        out = frame.copy()
        for r in zones(boxes, names, persons) + self.faces(frame):
            pixelate(out, r)
        return out
