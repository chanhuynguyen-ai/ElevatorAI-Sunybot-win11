from typing import Any

import requests
from fastapi import HTTPException

from elevator_gateway import config


def agent_url(path: str) -> str:
    return f"{config.AGENT_SERVICE_URL}{path}"


def vision_url(path: str) -> str:
    return f"{config.VISION_SERVICE_URL}{path}"


def request_json(method: str, url: str, *, timeout: float | None = None, **kwargs: Any) -> Any:
    try:
        response = requests.request(
            method,
            url,
            timeout=config.REQUEST_TIMEOUT if timeout is None else timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"upstream unavailable: {exc}") from exc


def service_available(url: str, timeout: float = 1.0) -> bool:
    try:
        return requests.get(url, timeout=timeout).ok
    except requests.RequestException:
        return False
