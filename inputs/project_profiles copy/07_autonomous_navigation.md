1. Autonomous War-Torn Navigation System
[GitHub URL: https://github.com/abandonedmonk/Autonomous-War-Torn-Navigation-System]
[Tech Stack: Python, C++, YOLO, OpenCV, ArUco, shortest path algorithms, Arduino, serial communication, GIS]
[Keywords: robotics, autonomous navigation, path planning, OpenCV, YOLO, ArUco, Arduino, obstacle detection, geospatial systems]
- Built an autonomous rescue system for unmanned vehicles in war-torn environments using PyTorch and OpenCV, achieving **80\%** obstacle detection accuracy.
- Designed a multi-stage pipeline processing IR sensor and camera module inputs, computing the safest routing via a shortest path planning algorithm.
- Deployed optimized paths to a ground bot via Bluetooth and integrated a GIS dashboard for live remote monitoring across dynamic hazardous terrains.

### What the repo actually contains
The repo combines vision-based event detection, map/path planning, and embedded control. One script runs YOLO-based event detection and assigns semantic labels such as combat, fire, destroyed buildings, and military vehicles. Another script performs ArUco-marker localization, CSV-based coordinate tracking, and graph-based route updates. An Arduino sketch under `Arduino/` supports the robot-side integration.

### Core architecture
- `Object_Detection_5B.py` loads a YOLO model, detects hazard/event classes from webcam frames, sorts detections spatially, and maps them to event identifiers.
- `PathPlanning_5B.py` defines the graph structure, ArUco dictionary, CSV I/O, marker-distance logic, and path-tracking workflow.
- `Arduino/Arduino.ino` represents the embedded handoff for robot execution.

### Repo-backed implementation details
The path-planning script uses an explicit adjacency matrix, location CSVs, ArUco-based position estimation, and serial communication hooks for the bot-control side. The event detector organizes detections into domain-specific labels, which matches the README’s emphasis on threat identification and path optimization. The GIS dashboard and Bluetooth claims are captured in the README and master inventory rather than in an isolated UI module.

### Resume-safe metrics
Preserve **80\%** exactly from the verified master inventory. The repo clearly supports the robotics, path-planning, and hazard-detection story, even though the exact evaluation protocol is not captured in code.

### ATS keywords
Autonomous navigation, robotics, OpenCV, YOLO, ArUco, path planning, shortest path, embedded systems, Arduino, geospatial monitoring.
