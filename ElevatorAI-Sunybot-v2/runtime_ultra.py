from app import config


class DetectorUltra:
    def __init__(self):
        from ultralytics import YOLO
        self.model = YOLO(config.DET_MODEL_DEV)

    def predict(self, frame):
        result = self.model.predict(
            frame,
            imgsz=config.DET_IMGSZ,
            conf=config.DET_CONF,
            iou=config.DET_IOU,
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


class PoseUltra:
    def __init__(self):
        from ultralytics import YOLO
        self.model = YOLO(config.POSE_MODEL_DEV)

    def predict(self, frame):
        result = self.model.predict(
            frame,
            imgsz=config.POSE_IMGSZ,
            conf=config.POSE_CONF,
            iou=config.POSE_IOU,
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
