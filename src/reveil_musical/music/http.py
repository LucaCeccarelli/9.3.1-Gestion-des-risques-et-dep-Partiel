"""Client HTTP minimal (stdlib) derrière une interface, pour pouvoir le remplacer en test."""

import json
from typing import Any, Mapping, Protocol
from urllib.request import Request, urlopen


class HttpClient(Protocol):
    def get_json(self, url: str, headers: Mapping[str, str] | None = None) -> Any: ...


class UrllibHttpClient:
    def __init__(self, timeout: float = 5.0) -> None:
        self._timeout = timeout

    def get_json(self, url: str, headers: Mapping[str, str] | None = None) -> Any:
        request = Request(url, headers=dict(headers or {}))
        with urlopen(request, timeout=self._timeout) as response:  # noqa: S310 (https only)
            return json.load(response)
