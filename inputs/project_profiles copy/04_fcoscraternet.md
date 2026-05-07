1. FCOSCraterNet: Dense Lunar Crater Detection
[GitHub URL: https://github.com/abandonedmonk/Lunar-Crater-Detection-using-Swin-Transformer]
[Tech Stack: Python, PyTorch, Swin Transformer, BiFPN, ASPP, Modal, OpenCV, CUDA]
[Keywords: computer vision, object detection, PyTorch, Swin Transformer, BiFPN, ASPP, FCOS, dense prediction, geospatial imagery]
- Architected a dense object detection model from scratch, integrating a Swin Transformer backbone with Atrous Spatial Pyramid Pooling (ASPP) and a BiFPN decoder.
- Engineered a **6**-stage dynamic loss schedule coupling Balanced L1 and DIoU objectives, using size-stratified gradient weighting to counteract target under-representation.
- Achieved a **68.8\%** F1 score on the DeepMoon benchmark dataset, driving a substantial precision increase from **72\%** to **77\%** by algorithmically suppressing false positives.

### What the repo actually contains
The repo is a full crater-detection training stack for the DeepMoon dataset. It includes the production FCOS model, a baseline vanilla model, dataset loaders, Modal-based training entrypoints, debugging tests, and detailed technical docs that explain architecture choices and the active training schedule.

### Core architecture
- `model_fcos.py` implements the production FCOS-style crater detector with classification, centerness, and distance-regression heads.
- `dataset_fcos.py` prepares crater targets and training data.
- `train_deep_moon.py` owns the active training loop and loss-weight schedule.
- `docs/README.md` and `docs/THREE_PHASE_TRAINING.md` document the Swin backbone, ASPP bottleneck, repeated BiFPN fusion, and staged Balanced L1/DIoU weighting.
- `test/` contains targeted checks for BiFPN behavior, overlap distance, dynamic sigma handling, VRAM analysis, and environment setup.

### Repo-backed implementation details
The docs describe a dense predictor that takes `256x256` inputs, extracts multi-scale Swin features, enriches the deepest map with ASPP, fuses scales through repeated weighted BiFPN layers, and upsamples to full-resolution crater maps. The implemented training schedule is explicitly multi-stage over `70` epochs, with Balanced L1 warmup and DIoU introduced later for geometric refinement. This is strong material for resume bullets because it proves you were shaping loss behavior and detector architecture rather than just fine-tuning a canned model.

### Resume-safe metrics
Preserve **6**, **68.8\%**, **72\%**, and **77\%** exactly from the verified master inventory. The repo’s docs independently support the presence of a staged loss schedule and custom architecture decisions.

### ATS keywords
PyTorch, object detection, Swin Transformer, BiFPN, ASPP, FCOS, dense prediction, loss engineering, geospatial imagery, Modal, OpenCV.
