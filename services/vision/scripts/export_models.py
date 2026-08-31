from ultralytics import YOLO

YOLO("models/yolov8n.pt").export(format="onnx", imgsz=320, opset=12, simplify=True)
YOLO("models/yolov8n-pose.pt").export(format="onnx", imgsz=384, opset=12, simplify=True)
