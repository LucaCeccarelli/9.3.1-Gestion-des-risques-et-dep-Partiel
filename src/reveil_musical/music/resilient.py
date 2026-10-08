"""Décorateurs de fournisseurs : cache (respect du rate-limit) et chaîne de secours."""

import logging
import time
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
        self._cache: dict[str, tuple[float, Track]] = {}

    def find(self, query: str) -> Track | None:
        now = self._clock()
        hit = self._cache.get(query)
        if hit and hit[0] > now:
            return hit[1]
        track = self._inner.find(query)
        if track is not None:
            self._cache[query] = (now + self._ttl, track)
        return track


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
            except Exception:  # noqa: BLE001 — toute panne => fournisseur suivant
                log.warning("fournisseur %s en panne", type(provider).__name__, exc_info=True)
                continue
            if track is not None:
                return track
        return None
