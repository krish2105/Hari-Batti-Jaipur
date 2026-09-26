# HariBatti — computer vision evaluation (W4)

> UVH-26 validation split (IISc, CC BY 4.0), seeded random sample: 400 images, 4,829 labelled vehicles · Apple silicon GPU (MPS), 55 ms per 1080p image (RT-DETRv2-S, 640 px input)

## Detection accuracy (MODEL, validation data)

| Model | mAP50:95 | mAP50 | Licence |
| --- | --- | --- | --- |
| RT-DETRv2-S, IISc UVH-26 weights · 14 Indian classes | 0.611 | 0.685 | Apache-2.0 |
| RT-DETRv2-S, IISc UVH-26 weights · 5 common classes | 0.745 | 0.859 | Apache-2.0 |
| RT-DETRv2-S, COCO weights (baseline) · 5 common classes | 0.339 | 0.518 | Apache-2.0 |

Common classes: car = Hatchback+Sedan+SUV+MUV+Van, bus = Bus+Mini-bus, truck = Truck+LCV, motorcycle = Two-wheeler; Three-wheeler, Tempo-traveller and Others are ignore regions. Evaluated with pycocotools on the UVH-26 validation split (not used to fit the weights; it may have guided IISc's model selection, so treat these as validation scores).

## Per class (IISc UVH-26 weights, 14 classes)

| Class | AP50:95 | Boxes in sample |
| --- | --- | --- |
| Hatchback | 0.692 | 462 |
| Sedan | 0.716 | 250 |
| SUV | 0.596 | 192 |
| MUV | 0.595 | 120 |
| Bus | 0.764 | 157 |
| Truck | 0.656 | 168 |
| Three-wheeler | 0.842 | 803 |
| Two-wheeler | 0.777 | 2,259 |
| LCV | 0.722 | 292 |
| Mini-bus | 0.304 | 13 |
| Tempo-traveller | 0.589 | 20 |
| Bicycle | 0.577 | 49 |
| Van | 0.642 | 36 |
| Others | 0.083 | 8 |

## Pipeline

- **privacy**: Faces (YuNet) and number-plate zones blurred before any frame is saved; no ANPR, no identity tracking
- **tracking**: ByteTrack (supervision, MIT)
- **outputs**: turning counts (tmc_clean.csv schema, source FIELD), queue per approach per second, saturation flow, signal state from a lamp ROI

## Video runs (aggregates only; frames are never published)

| Clip | Seconds | Linked movements | Arm volumes (veh/h, both directions) | Pedestrian crossings | Source |
| --- | --- | --- | --- | --- | --- |
| cuttack_link_road.webm | 134 | 39 | Right arm 1,266, Centre-back arm 2,531, Foreground arm (camera side) 2,585, Far-left arm 1,427 | 92 | FIELD (demo clip, not a pilot junction) |

The demo clip shows Link Road, Cuttack (Wikimedia Commons, CC BY-SA 3.0, Subhashish Panigrahi): a demo of tracking and counting, not a pilot junction. Its signal lamps face away from the camera, so signal state and saturation flow are reported as not measured. Your own clip: `make cv-video VIDEO=clip.mp4 JUNCTION=J05`.
