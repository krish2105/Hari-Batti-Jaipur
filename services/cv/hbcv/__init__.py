"""HariBatti computer vision (W4). Read-only: it watches a recorded junction video, it never
touches a signal. Faces and number-plate zones are blurred before any frame is written to disk.

fetch.py     download the RT-DETR code, the released weights and a UVH-26 validation sample
detector.py  RT-DETRv2 inference (IISc UVH-26 weights, 14 Indian vehicle classes; COCO baseline)
evaluate.py  mAP50:95 on the UVH-26 sample vs the COCO baseline -> reports/cv_eval.json
privacy.py   face + plate-zone blur (always applied before saving)
video.py     tracking, turning counts, queues, saturation flow, signal state -> `make cv-video`
"""
