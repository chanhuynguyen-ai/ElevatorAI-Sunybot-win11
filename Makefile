.PHONY: test check smoke

test:
	PYTHONPATH=services/vision/src pytest -q services/vision/tests
	PYTHONPATH=services/agent/src pytest -q services/agent/tests
	PYTHONPATH=services/gateway/src pytest -q services/gateway/tests

check:
	python scripts/check_repo.py

smoke:
	python scripts/smoke_http.py
