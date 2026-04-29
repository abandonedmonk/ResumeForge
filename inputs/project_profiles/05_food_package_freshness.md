1. Food Package and Freshness Detection
[GitHub URL: https://github.com/abandonedmonk/Food-Package-and-Freshness-Detection]
[Tech Stack: Python, Streamlit, YOLO, OpenCV, Groq, Vision-Language Models, OCR]
[Keywords: multimodal AI, YOLO, OpenCV, Streamlit, VLM, OCR, freshness detection, packaging analysis, computer vision]
- Built a cross-modal computer vision system integrating YOLO object detection and LLaMA to analyze raw food freshness and product packaging, achieving **90\%** accuracy.
- Engineered an interactive multimodal pipeline to bridge visual classification of ripeness stages with generative NLP for structured data extraction.
- Extracted key product details including brand, ingredients, nutrition, expiry dates, and allergen warnings from complex, unstructured visual inputs.

### What the repo actually contains
The project is implemented as a Streamlit application that switches between tomato freshness analysis and packet analysis. It loads separate YOLO models for tomatoes and packets, uses a center-point tracker for packet identities, crops packet detections, converts them to base64 images, and sends them to a Groq-hosted vision model for packaging detail extraction. Output artifacts are stored in a `results/` directory as text reports.

### Core architecture
- `final_stream.py` contains the end-to-end app, model loading, image/video/live-feed handling, tracking, counting logic, and asynchronous VLM analysis queue.
- `results/` stores structured extraction outputs for detected packets.
- `test_data/` includes example packet and tomato images for manual testing.

### Repo-backed implementation details
The tomato path classifies six ripeness-related classes and aggregates them into fresh vs. not-fresh counts. The packet path performs asynchronous queue-based analysis so detection and VLM extraction do not block each other. The code also writes per-frame, per-object analysis files with timestamps, which is useful proof of a structured multimodal extraction pipeline rather than a toy demo.

### Resume-safe metrics
Preserve **90\%** from the verified master inventory. The repo clearly supports the YOLO + VLM + structured extraction story even though the exact score is not reported in code.

### ATS keywords
YOLO, OpenCV, Streamlit, multimodal AI, vision-language model, OCR, structured extraction, image processing, object tracking.
