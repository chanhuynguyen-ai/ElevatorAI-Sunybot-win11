# Validation status

This repository is intentionally validated in layers so a reviewer can distinguish what was actually exercised from what requires target hardware.

## Executed during consolidation

- Vision unit/API tests: **4 passed**
- Agent routing/policy/normalization tests: **3 passed**
- Gateway health/proxy/security tests: **3 passed**
- Python compilation: Vision, Agent and Gateway passed
- Python 3.6 grammar compatibility check: Vision and Agent passed (for JetPack 4-era source compatibility)
- Local HTTP integration smoke: Gateway -> Agent and Gateway -> Vision passed using the hardware-free mock CV runtime
- Compose/override/CI YAML parsing: passed
- Frontend `package.json` + lockfile JSON validation: passed
- Frontend relative-import resolution: passed
- Secret/merge-conflict/generated-artifact scan: passed after cleanup

## Requires external environment

The current sandbox does not provide Docker, PostgreSQL, a camera, Jetson/TensorRT, Ollama, or reliable npm registry access. Therefore these paths are configured and CI-covered but were **not claimed as locally hardware-tested**:

- Docker Compose full-stack build
- React/Vite rebuild from npm registry
- Laptop Ultralytics inference with a physical webcam
- Jetson Nano TensorRT/GStreamer inference
- PostgreSQL-backed RAG/Data Manager against a live database
- Ollama generative responses

The GitHub Actions workflow contains a full Compose smoke job so the clean-clone Docker path can be verified automatically after the repository is pushed.
