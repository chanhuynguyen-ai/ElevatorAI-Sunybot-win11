import numpy as np
import tensorrt as trt
import pycuda.driver as cuda

from app import config
from app.yolo_utils import preprocess_bgr, parse_det_output, parse_pose_output


class TRTEngine:
    def __init__(self, engine_path):
        self.engine_path = engine_path
        self.logger = trt.Logger(trt.Logger.WARNING)

        self.cuda_ctx = None
        self.runtime = None
        self.engine = None
        self.context = None
        self.stream = None

        self.bindings = []
        self.host_inputs = []
        self.cuda_inputs = []
        self.host_outputs = []
        self.cuda_outputs = []
        self.output_shapes = []
        self.initialized = False

    def initialize(self):
        if self.initialized:
            return

        cuda.init()
        self.cuda_ctx = cuda.Device(0).make_context()
        try:
            with open(self.engine_path, "rb") as f:
                self.runtime = trt.Runtime(self.logger)
                self.engine = self.runtime.deserialize_cuda_engine(f.read())
            if self.engine is None:
                raise RuntimeError("Khong the deserialize TensorRT engine: %s" % self.engine_path)

            self.context = self.engine.create_execution_context()
            if self.context is None:
                raise RuntimeError("Khong the tao execution context cho engine: %s" % self.engine_path)

            self.stream = cuda.Stream()
            self.bindings = []
            self.host_inputs = []
            self.cuda_inputs = []
            self.host_outputs = []
            self.cuda_outputs = []
            self.output_shapes = []

            for binding in self.engine:
                shape = tuple(self.engine.get_binding_shape(binding))
                dtype = trt.nptype(self.engine.get_binding_dtype(binding))
                size = int(trt.volume(shape))
                host_mem = cuda.pagelocked_empty(size, dtype)
                cuda_mem = cuda.mem_alloc(host_mem.nbytes)
                self.bindings.append(int(cuda_mem))

                if self.engine.binding_is_input(binding):
                    self.host_inputs.append(host_mem)
                    self.cuda_inputs.append(cuda_mem)
                else:
                    self.output_shapes.append(shape)
                    self.host_outputs.append(host_mem)
                    self.cuda_outputs.append(cuda_mem)

            self.initialized = True
        finally:
            # make_context() pushes the context; leave the thread clean after init
            self.cuda_ctx.pop()

    def infer(self, x):
        if not self.initialized:
            self.initialize()

        self.cuda_ctx.push()
        try:
            np.copyto(self.host_inputs[0], x.ravel())
            cuda.memcpy_htod_async(self.cuda_inputs[0], self.host_inputs[0], self.stream)
            ok = self.context.execute_async_v2(bindings=self.bindings, stream_handle=self.stream.handle)
            if not ok:
                raise RuntimeError("TensorRT execute_async_v2 tra ve False")

            for host_out, cuda_out in zip(self.host_outputs, self.cuda_outputs):
                cuda.memcpy_dtoh_async(host_out, cuda_out, self.stream)
            self.stream.synchronize()

            outputs = []
            for host_out, shape in zip(self.host_outputs, self.output_shapes):
                outputs.append(host_out.reshape(shape).copy())
            return outputs
        finally:
            self.cuda_ctx.pop()

    def destroy(self):
        if self.cuda_ctx is None:
            return
        self.cuda_ctx.push()
        try:
            try:
                if self.stream is not None:
                    self.stream.synchronize()
            except Exception:
                pass
            for mem in self.cuda_inputs + self.cuda_outputs:
                try:
                    mem.free()
                except Exception:
                    pass
            self.cuda_inputs = []
            self.cuda_outputs = []
            self.host_inputs = []
            self.host_outputs = []
        finally:
            self.cuda_ctx.pop()
            self.cuda_ctx.detach()
            self.cuda_ctx = None
            self.initialized = False


class DetectorTRT:
    def __init__(self):
        self.engine = TRTEngine(config.DET_ENGINE_PATH)

    def predict(self, frame):
        x, ratio, dwdh = preprocess_bgr(frame, config.DET_IMGSZ)
        raw = self.engine.infer(x)[0]
        return parse_det_output(raw, ratio, dwdh, frame.shape, config.DET_CONF, config.DET_IOU)

    def destroy(self):
        self.engine.destroy()


class PoseTRT:
    def __init__(self):
        self.engine = TRTEngine(config.POSE_ENGINE_PATH)

    def predict(self, frame):
        x, ratio, dwdh = preprocess_bgr(frame, config.POSE_IMGSZ)
        raw = self.engine.infer(x)[0]
        return parse_pose_output(raw, ratio, dwdh, frame.shape, config.POSE_CONF, config.POSE_IOU)

    def destroy(self):
        self.engine.destroy()
