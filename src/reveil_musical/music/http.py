"""Client HTTP minimal (stdlib) derrière une interface, pour pouvoir le remplacer en test."""

import json
from collections.abc import Mapping
from typing import Any, Protocol
from urllib.request import Request, urlopen


class HttpClient(Protocol):
    def get_json(self, url: str, headers: Mapping[str, str] | None = None) -> Any: ...


class UrllibHttpClient:
    def __init__(self, timeout: float = 5.0) -> None:
        self._timeout = timeout

    def get_json(self, url: str, headers: Mapping[str, str] | None = None) -> Any:
        request = Request(url, headers=dict(headers or {}))  # noqa: S310 — https uniquement
        with urlopen(request, timeout=self._timeout) as response:  # noqa: S310
            return json.load(response)
