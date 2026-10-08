import pytest

from reveil_musical.domain import Track
from reveil_musical.music.itunes import ITunesMusicProvider
from reveil_musical.music.local import LocalMusicProvider
from reveil_musical.music.musicbrainz import MusicBrainzMusicProvider
from reveil_musical.music.resilient import (
    CachedMusicProvider,
    FallbackChainMusicProvider,
    RateLimitedMusicProvider,
)
from tests.conftest import FakeHttp, FakeMusic

ITUNES = {
    "results": [{"trackName": "Here Comes the Sun", "artistName": "The Beatles", "trackViewUrl": "x"}]
}
MB = {
    "recordings": [
        {"title": "Lovely Day", "artist-credit": [{"name": "Bill", "joinphrase": " & "}, {"name": "Withers"}]}
    ]
}


def test_itunes_maps_response_without_leaking_url():
    http = FakeHttp(ITUNES)
    track = ITunesMusicProvider(http).find("here comes")
    assert track == Track("Here Comes the Sun", "The Beatles")
    url = http.requests[0][0]
    assert "term=here+comes" in url and "media=music" in url and "limit=5" in url


def test_itunes_empty_results():
    assert ITunesMusicProvider(FakeHttp({"resultCount": 0, "results": []})).find("x") is None


def test_musicbrainz_sets_user_agent_and_joins_artists():
    http = FakeHttp(MB)
    track = MusicBrainzMusicProvider(http, "App/1 (me@x)").find("lovely")
    assert track == Track("Lovely Day", "Bill & Withers")
    assert http.requests[0][1]["User-Agent"] == "App/1 (me@x)"
    assert "fmt=json" in http.requests[0][0]


def test_musicbrainz_skips_incomplete():
    http = FakeHttp({"recordings": [{"title": "no artist"}]})
    assert MusicBrainzMusicProvider(http, "ua").find("x") is None


def test_local_matches_title_else_first_of_list():
    local = LocalMusicProvider()
    assert local.find("lovely day") == Track("Lovely Day", "Bill Withers")
    assert local.find("zzz") == Track("Here Comes the Sun", "The Beatles")


def test_local_requires_tracks():
    with pytest.raises(ValueError):
        LocalMusicProvider(())


def test_cache_hits_until_ttl_expires():
    inner = FakeMusic(Track("a", "b"))
    now = [0.0]
    cached = CachedMusicProvider(inner, ttl_seconds=10, clock=lambda: now[0])
    cached.find("q")
    cached.find("q")
    assert inner.calls == ["q"]
    now[0] = 11
    cached.find("q")
    assert inner.calls == ["q", "q"]


def test_cache_stores_misses_but_not_failures():
    inner = FakeMusic(None)
    cached = CachedMusicProvider(inner)
    assert cached.find("q") is cached.find("q") is None
    assert inner.calls == ["q"]
    down = FakeMusic(error=OSError("down"))
    cached = CachedMusicProvider(down)
    for _ in range(2):
        with pytest.raises(OSError):
            cached.find("q")
    assert down.calls == ["q", "q"]


def test_rate_limit_blocks_beyond_quota_then_releases():
    inner = FakeMusic(Track("a", "b"))
    now = [0.0]
    limited = RateLimitedMusicProvider(inner, max_calls=2, period=60, clock=lambda: now[0])
    assert limited.find("q1") == limited.find("q2") == Track("a", "b")
    with pytest.raises(RuntimeError):  # quota atteint : pas d'appel, la chaîne passera au suivant
        limited.find("q3")
    assert inner.calls == ["q1", "q2"]
    now[0] = 61
    assert limited.find("q4") == Track("a", "b")
    assert inner.calls == ["q1", "q2", "q4"]


def test_chain_skips_failing_and_empty_providers():
    down = FakeMusic(error=ConnectionError("boom"))
    empty = FakeMusic(None)
    ok = FakeMusic(Track("x", "y"))
    assert FallbackChainMusicProvider([down, empty, ok]).find("q") == Track("x", "y")
    assert down.calls == empty.calls == ok.calls == ["q"]


def test_chain_returns_none_when_all_empty():
    assert FallbackChainMusicProvider([FakeMusic(None)]).find("q") is None


def test_chain_requires_providers():
    with pytest.raises(ValueError):
        FallbackChainMusicProvider([])


def test_chain_with_local_completes_known_title():
    chain = FallbackChainMusicProvider([FakeMusic(error=OSError()), LocalMusicProvider()])
    assert chain.find("good morning") == Track("Good Morning", "Gene Kelly")
