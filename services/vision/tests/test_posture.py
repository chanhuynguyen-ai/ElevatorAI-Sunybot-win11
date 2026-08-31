import numpy as np
from elevator_vision.posture import classify_posture

def test_posture_returns_supported_label():
    kpts = np.zeros((17, 3), dtype=float)
    label, meta = classify_posture(kpts, [0,0,100,200], return_meta=True)
    assert label in {"unknown", "standing", "sitting", "lying", "bending"}
    assert isinstance(meta, dict)
