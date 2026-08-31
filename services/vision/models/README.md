# Model artifacts

Model binaries are intentionally not committed to keep the repository portable and to avoid shipping device-specific TensorRT engines.

Laptop development:
1. Install `ultralytics`.
2. Put/download `yolov8n.pt` and `yolov8n-pose.pt` here.
3. Set `CV_BACKEND=ultralytics`.

Jetson Nano:
1. Export the `.pt` files to ONNX with `python scripts/export_models.py` on a development machine.
2. Copy the ONNX files into this directory on the Jetson.
3. Run `scripts/build_engines.sh` **on the target Jetson Nano**.
4. Set `CV_BACKEND=trt`.

`.engine` files are ignored because TensorRT engines are hardware/runtime specific.
