import os

from app import config


class _BaseUltra:
    def __init__(self, model_path):
        from ultralytics import YOLO

        self.model = YOLO(model_path)
        self.device = self._resolve_device()
        self.use_half = bool(getattr(config, 'YOLO_USE_HALF', False) and self.device != 'cpu')

    def _resolve_device(self):
        requested = str(getattr(config, 'CV_DEVICE', 'auto') or 'auto').strip().lower()
        try:
            import torch
            has_cuda = bool(torch.cuda.is_available() and torch.cuda.device_count() > 0)
        except Exception:
            has_cuda = False

        if requested in {'', 'auto'}:
            return 0 if has_cuda else 'cpu'
        if requested in {'cpu', '-1'}:
            return 'cpu'
        if requested.startswith('cuda'):
            return requested if has_cuda else 'cpu'
        if requested.isdigit():
            return int(requested) if has_cuda else 'cpu'
        return requested


class DetectorUltra(_BaseUltra):
    def __init__(self):
        super().__init__(config.DET_MODEL_DEV)

    def predict(self, frame):
        result = self.model.predict(
            frame,
            imgsz=config.DET_IMGSZ,
            conf=config.DET_CONF,
            iou=config.DET_IOU,
            device=self.device,
            half=self.use_half,
            verbose=False,
        )[0]
        out = []
        boxes = result.boxes
        if boxes is None:
            return out
        xyxy = boxes.xyxy.cpu().numpy().astype(int)
        confs = boxes.conf.cpu().numpy()
        clss = boxes.cls.cpu().numpy().astype(int)
        for b, c, k in zip(xyxy, confs, clss):
            out.append({"bbox": b.tolist(), "conf": float(c), "cls": int(k)})
        return out


class PoseUltra(_BaseUltra):
    def __init__(self):
        super().__init__(config.POSE_MODEL_DEV)

    def predict(self, frame):
        result = self.model.predict(
            frame,
            imgsz=config.POSE_IMGSZ,
            conf=config.POSE_CONF,
            iou=config.POSE_IOU,
            device=self.device,
            half=self.use_half,
            verbose=False,
        )[0]
        out = []
        boxes = result.boxes
        kpts = result.keypoints
        if boxes is None or kpts is None:
            return out
        xyxy = boxes.xyxy.cpu().numpy().astype(int)
        confs = boxes.conf.cpu().numpy()
        kp = kpts.data.cpu().numpy()
        for b, c, kk in zip(xyxy, confs, kp):
            out.append({"bbox": b.tolist(), "conf": float(c), "keypoints": kk.tolist()})
        return out
