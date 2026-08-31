import cv2
import numpy as np



def letterbox(im, new_shape=640, color=(114, 114, 114)):
    h, w = im.shape[:2]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)
    r = min(new_shape[0] / h, new_shape[1] / w)
    nw, nh = int(round(w * r)), int(round(h * r))
    dw, dh = new_shape[1] - nw, new_shape[0] - nh
    dw /= 2
    dh /= 2

    resized = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    out = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return out, r, (dw, dh)



def preprocess_bgr(frame, imgsz):
    img, ratio, dwdh = letterbox(frame, imgsz)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.transpose(2, 0, 1)
    img = np.ascontiguousarray(img, dtype=np.float32) / 255.0
    return img[None], ratio, dwdh



def xywh2xyxy(x):
    y = x.copy()
    y[:, 0] = x[:, 0] - x[:, 2] / 2
    y[:, 1] = x[:, 1] - x[:, 3] / 2
    y[:, 2] = x[:, 0] + x[:, 2] / 2
    y[:, 3] = x[:, 1] + x[:, 3] / 2
    return y



def nms_numpy(boxes, scores, iou_thresh):
    idxs = scores.argsort()[::-1]
    keep = []
    while idxs.size > 0:
        i = idxs[0]
        keep.append(i)
        if idxs.size == 1:
            break
        rest = idxs[1:]
        xx1 = np.maximum(boxes[i, 0], boxes[rest, 0])
        yy1 = np.maximum(boxes[i, 1], boxes[rest, 1])
        xx2 = np.minimum(boxes[i, 2], boxes[rest, 2])
        yy2 = np.minimum(boxes[i, 3], boxes[rest, 3])

        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        area_r = (boxes[rest, 2] - boxes[rest, 0]) * (boxes[rest, 3] - boxes[rest, 1])
        iou = inter / (area_i + area_r - inter + 1e-6)
        idxs = rest[iou < iou_thresh]
    return keep



def scale_boxes(boxes, ratio, dwdh, orig_shape):
    boxes = boxes.copy()
    boxes[:, [0, 2]] -= dwdh[0]
    boxes[:, [1, 3]] -= dwdh[1]
    boxes[:, :4] /= ratio
    h, w = orig_shape[:2]
    boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, w - 1)
    boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, h - 1)
    return boxes



def parse_det_output(raw, ratio, dwdh, orig_shape, conf=0.35, iou=0.45):
    out = np.squeeze(raw)
    if out.ndim == 2 and out.shape[0] < out.shape[1]:
        out = out.T
    if out.ndim != 2:
        return []

    boxes = xywh2xyxy(out[:, :4])
    cls_scores = out[:, 4:]
    cls_ids = cls_scores.argmax(axis=1)
    scores = cls_scores.max(axis=1)

    mask = scores >= conf
    boxes = boxes[mask]
    scores = scores[mask]
    cls_ids = cls_ids[mask]

    if len(boxes) == 0:
        return []

    boxes = scale_boxes(boxes, ratio, dwdh, orig_shape)
    keep = nms_numpy(boxes, scores, iou)

    results = []
    for i in keep:
        results.append({
            "bbox": boxes[i].astype(int).tolist(),
            "conf": float(scores[i]),
            "cls": int(cls_ids[i]),
        })
    return results



def parse_pose_output(raw, ratio, dwdh, orig_shape, conf=0.35, iou=0.45):
    out = np.squeeze(raw)
    if out.ndim == 2 and out.shape[0] < out.shape[1]:
        out = out.T
    if out.ndim != 2 or out.shape[1] < 56:
        return []

    boxes = xywh2xyxy(out[:, :4])
    scores = out[:, 4]
    kpts = out[:, 5:56].reshape(-1, 17, 3)

    mask = scores >= conf
    boxes = boxes[mask]
    scores = scores[mask]
    kpts = kpts[mask]
    if len(boxes) == 0:
        return []

    boxes = scale_boxes(boxes, ratio, dwdh, orig_shape)
    keep = nms_numpy(boxes, scores, iou)

    results = []
    for i in keep:
        kp = kpts[i].copy()
        kp[:, 0] = (kp[:, 0] - dwdh[0]) / ratio
        kp[:, 1] = (kp[:, 1] - dwdh[1]) / ratio
        results.append({
            "bbox": boxes[i].astype(int).tolist(),
            "conf": float(scores[i]),
            "keypoints": kp.tolist(),
        })
    return results
