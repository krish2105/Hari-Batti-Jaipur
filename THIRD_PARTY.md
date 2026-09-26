# Third-party data, models and assets

| Item | Used for | Licence | Attribution |
| --- | --- | --- | --- |
| OpenStreetMap data | Map, road network, candidate coordinates | ODbL 1.0 | © OpenStreetMap contributors |
| OpenFreeMap tiles and styles | Website map | Free tiles; OpenMapTiles schema | OpenFreeMap © OpenMapTiles |
| Eclipse SUMO | Traffic simulation | EPL-2.0 | Eclipse Foundation |
| Fonts: Fraunces, Inter, Noto Sans Devanagari, Doto | Website typography | SIL OFL 1.1 | Google Fonts |
| three.js + Draco decoder (`apps/web/public/draco/`) | 3D rendering, compressed meshes | MIT / Apache-2.0 | three.js authors, Google Draco |
| glTF-Transform | GLB compression (build tool) | MIT | Don McCurdy |
| VT-Micro fuel/CO2 coefficients | Green-wave demo estimate | Published research (Ahn et al., 2002, J. Transp. Eng.) | Coefficient tables as reprinted in arXiv:2305.00750 |
| 3D vehicles, buildings, signal pole | Website | Original work (tools/blender, this repo) | Generic designs, no brands or logos |

| Optuna | Calibration search (W1) | MIT | Preferred Networks |
| sumo-rl | Signal-control environments (W2) | MIT | Lucas N. Alegre |
| Stable-Baselines3 | PPO agents (W2) | MIT | DLR-RM |
| Gymnasium, PettingZoo | RL interfaces used by sumo-rl (W2) | MIT | Farama Foundation |
| libsumo | In-process SUMO for training (W2) | EPL-2.0 (used under EPL-2.0) | Eclipse Foundation |
| PyTorch, torchvision | PPO networks, RT-DETRv2, forecasting net | BSD-3-Clause / Apache-2.0 | PyTorch contributors |
| LightGBM | Demand forecasting (W5) | MIT | Microsoft |
| scikit-learn | Isolation forest, analytics | BSD-3-Clause | scikit-learn developers |
| RT-DETR / RT-DETRv2 code (github.com/lyuwenyu/RT-DETR, cloned at setup, not vendored in git) | Vehicle detector (W4) | Apache-2.0 | Wenyu Lv et al. |
| RT-DETRv2-S COCO weights (`rtdetrv2_r18vd_120e_coco_rerun_48.1.pth`) | Baseline detector, pedestrians (W4) | Apache-2.0 | Wenyu Lv et al. |
| UVH-26 RT-DETRv2-S weights (`UVH-26-MV-RT-DETRv2-S.pth`, huggingface.co/iisc-aim/UVH-26) | Indian vehicle detector, 14 classes (W4) | Apache-2.0 | AIM @ IISc, Bengaluru. The same repository's YOLO weights are AGPL-3.0 and are **not** used. |
| UVH-26 dataset, validation split (400-image seeded sample, not redistributed) | Detector evaluation (W4) | CC BY 4.0 | AIM @ IISc, "The Urban Vision Hackathon Dataset and Models", arXiv:2511.02563 |
| YuNet face detector (`face_detection_yunet_2023mar.onnx`, OpenCV Zoo) | Privacy blur before storage (W4) | MIT | OpenCV Zoo / Shiqi Yu et al. |
| OpenCV (opencv-python-headless) | Video I/O, blur | Apache-2.0 | OpenCV team |
| supervision | ByteTrack tracking, drawing (W4) | MIT | Roboflow |
| pycocotools, faster-coco-eval | mAP evaluation (W4) | BSD-2-Clause / Apache-2.0 | COCO consortium; MiXaiLL76 |
| Video "Moving vehicles in Link road, Cuttack, Odisha" (Wikimedia Commons) | Tracking/count demo only; only aggregate numbers are kept, no frames or derived video are published | CC BY-SA 3.0 | Subhashish Panigrahi |
| paho-mqtt | MQTT subscribe-only connector (W12) | EPL-2.0 OR BSD-3-Clause (dual); **used under BSD-3-Clause** | Eclipse Foundation / Roger Light et al. |
| websockets | WebSocket push connector (W12) | BSD-3-Clause | Aymeric Augustin and contributors |
| openpyxl | Excel exports and timing sheets (W12) | MIT | openpyxl authors |
| pdfplumber, pdfminer.six (pypdfium2) | Timing-plan tables from PDFs (W12) | MIT / MIT (Apache-2.0 or BSD-3-Clause) | Jeremy Singer-Vine; pdfminer.six contributors; pypdfium2 contributors |
| PyYAML | Connector configuration (W12) | MIT | Kirill Simonov and contributors |
| SAE J2735 SPaT message layout | Decoding SPaT JSON (W12); only the public field names are used, no standard text is copied | Standard (SAE International) | SAE J2735 |
