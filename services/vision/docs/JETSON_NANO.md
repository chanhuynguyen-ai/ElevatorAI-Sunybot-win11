# Jetson Nano deployment

The legacy target is JetPack 4.x / Python 3.6. Keep TensorRT/CUDA/OpenCV/PyCUDA from JetPack rather than reinstalling them from pip.

1. Copy/export YOLO models to ONNX.
2. Run `scripts/build_engines.sh` on the target Nano.
3. Configure a CSI camera pipeline, for example:

```bash
export CAMERA_SOURCE='gst:nvarguscamerasrc sensor-id=0 ! video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1,format=NV12 ! nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! video/x-raw,format=BGR ! appsink drop=1 max-buffers=1 sync=false'
export CV_BACKEND=trt
export ENABLE_POSE=true
export CV_DB_ENABLED=true
```

4. Install only the legacy Python packages in `requirements/jetson-nano.txt` and start the service with `PYTHONPATH=src python3 -m elevator_vision`.
