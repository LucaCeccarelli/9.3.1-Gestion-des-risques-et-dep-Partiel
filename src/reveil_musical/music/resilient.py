"""Décorateurs de cache et de limitation de débit (Decorator), chaîne de secours (Chain of Responsibility)."""

import logging
import time
from collections import deque
from collections.abc import Callable, Sequence

from reveil_musical.domain import MusicProvider, Track

log = logging.getLogger(__name__)


class CachedMusicProvider:
    def __init__(
        self,
        inner: MusicProvider,
        ttl_seconds: float = 3600,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner = inner
        self._ttl = ttl_seconds
        self._clock = clock
        self._cache: dict[str, tuple[float, Track | None]] = {}

    def find(self, query: str) -> Track | None:
        now = self._clock()
        hit = self._cache.get(query)
        if hit and hit[0] > now:
            return hit[1]
        track = self._inner.find(query)  # une panne lève et n'est pas mémorisée
        self._cache[query] = (now + self._ttl, track)  # un titre inconnu l'est aussi
        return track


class RateLimitedMusicProvider:
    """Au plus `max_calls` appels par `period` secondes (fenêtre glissante) ; au-delà, lève
    sans appeler le fournisseur : indisponible, la chaîne passe au suivant. Protège un quota d'API."""

    def __init__(
        self,
        inner: MusicProvider,
        max_calls: int,
        period: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner = inner
        self._max_calls = max_calls
        self._period = period
        self._clock = clock
        self._calls: deque[float] = deque()

    def find(self, query: str) -> Track | None:
        now = self._clock()
        while self._calls and self._calls[0] <= now - self._period:
            self._calls.popleft()
        if len(self._calls) >= self._max_calls:
            raise RuntimeError(f"quota {type(self._inner).__name__} atteint")
        self._calls.append(now)
        return self._inner.find(query)


class FallbackChainMusicProvider:
    """Interroge les fournisseurs dans l'ordre ; une panne passe au suivant."""

    def __init__(self, providers: Sequence[MusicProvider]) -> None:
        if not providers:
            raise ValueError("au moins un fournisseur requis")
        self._providers = providers

    def find(self, query: str) -> Track | None:
        for provider in self._providers:
            try:
                track = provider.find(query)
            except Exception as exc:  # noqa: BLE001 — panne ou quota => fournisseur suivant
                log.warning("fournisseur %s indisponible : %s", type(provider).__name__, exc)
                continue
            if track is not None:
                return track
        return None
