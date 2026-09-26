"""Where the CV service keeps its (gitignored) downloads and its (committed) reports."""

from pathlib import Path

CV_DIR = Path(__file__).resolve().parents[1]  # services/cv
ROOT = CV_DIR.parents[1]
VENDOR = CV_DIR / "vendor" / "RT-DETR"  # lyuwenyu/RT-DETR, Apache-2.0, cloned by fetch.py
RTDETR_SRC = VENDOR / "rtdetrv2_pytorch"
WEIGHTS = CV_DIR / "weights"
DATA = CV_DIR / "data"
VAL_DIR = DATA / "uvh26-val"
REPORTS = CV_DIR / "reports"
OUT = CV_DIR / "out"  # results of `make cv-video` (blurred previews are safe; still not committed)

UVH_MODEL = WEIGHTS / "UVH-26-MV-RT-DETRv2-S.pth"
UVH_CONFIG = WEIGHTS / "rtdetrv2_s.yaml"
COCO_MODEL = WEIGHTS / "rtdetrv2_r18vd_120e_coco_rerun_48.1.pth"
FACE_MODEL = WEIGHTS / "face_detection_yunet_2023mar.onnx"  # OpenCV Zoo YuNet, MIT
PROFILES = CV_DIR / "profiles"  # camera profiles (zones, stop line, lamp ROI) - numbers only, committed
