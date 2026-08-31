#!/usr/bin/env bash
set -e

TRTEXEC=/usr/src/tensorrt/bin/trtexec

$TRTEXEC --onnx=models/yolov8n.onnx --saveEngine=models/yolov8n_fp16.engine --fp16 --workspace=1024 --skipInference
$TRTEXEC --onnx=models/yolov8n-pose.onnx --saveEngine=models/yolov8n_pose_fp16.engine --fp16 --workspace=1024 --skipInference
