REPLACE THESE FILES

- ElevatorAI-Sunybot-cv-v2/app/config.py
- ElevatorAI-Sunybot-cv-v2/app/posture.py
- ElevatorAI-Sunybot-cv-v2/app/camera_service.py

WHY THIS VERSION IS BETTER
- bent-over posture is no longer easily counted as standing
- new posture state: bending
- lying requires stronger score and more stable confirmation
- fall requires lying duration + smoothed motion + multi-frame confirmation
- better for Win11 CPU + webcam

SUGGESTED WIN11 ENV
set CV_BACKEND=ultralytics
set CV_DEVICE=cpu
set YOLO_USE_HALF=false
set ENABLE_FACE=true
set ENABLE_POSE=true
set POSE_EVERY_N=2
set YOLO_EVERY_N=2
set LYING_CONFIRM_FRAMES=4
set FALL_CONFIRM_FRAMES=2
set FALL_MIN_CENTER_DROP_RATIO=0.24
set FALL_MIN_VERTICAL_SPEED=155
set FALL_POSTURE_CONF_MIN=0.68

AFTER REPLACE
- restart CV backend
- Ctrl + F5 browser
