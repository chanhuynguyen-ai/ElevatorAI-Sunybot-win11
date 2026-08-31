class MockDetector:
    """No-op detector used for smoke tests and hardware-free demos."""
    def predict(self, frame):
        return []


class MockPose:
    def predict(self, frame):
        return []
