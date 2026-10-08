import pytest

from reveil_musical.domain import Track
from reveil_musical.music.itunes import ITunesMusicProvider
from reveil_musical.music.local import LOCAL_TRACKS, LocalMusicProvider
from reveil_musical.music.musicbrainz import MusicBrainzMusicProvider
from reveil_musical.music.resilient import CachedMusicProvider, FallbackChainMusicProvider
from tests.conftest import FakeHttp, FakeMusic

ITUNES = {"results": [{"trackName": "Here Comes the Sun", "artistName": "The Beatles", "trackViewUrl": "x"}]}
MB = {"recordings": [{"title": "Lovely Day", "artist-credit": [{"name": "Bill", "joinphrase": " & "}, {"name": "Withers"}]}]}


def test_itunes_maps_response_without_leaking_url():
    http = FakeHttp(ITUNES)
    track = ITunesMusicProvider(http).find("here comes")
    assert track == Track("Here Comes the Sun", "The Beatles")
    assert "term=here+comes" in http.requests[0][0] and "media=music" in http.requests[0][0]


def test_itunes_empty_results():
    assert ITunesMusicProvider(FakeHttp({"resultCount": 0, "results": []})).find("x") is None


def test_musicbrainz_sets_user_agent_and_joins_artists():
    http = FakeHttp(MB)
    track = MusicBrainzMusicProvider(http, "App/1 (me@x)").find("lovely")
    assert track == Track("Lovely Day", "Bill & Withers")
    assert http.requests[0][1]["User-Agent"] == "App/1 (me@x)"
    assert "fmt=json" in http.requests[0][0]


def test_musicbrainz_skips_incomplete():
    assert MusicBrainzMusicProvider(FakeHttp({"recordings": [{"title": "no artist"}]}), "ua").find("x") is None


def test_local_matches_title_or_picks_deterministically():
    local = LocalMusicProvider()
    assert local.find("lovely day").title == "Lovely Day"
    assert local.find("zzz") in LOCAL_TRACKS
    assert local.find("zzz") == local.find("zzz")


def test_cache_hits_until_ttl_expires():
    inner = FakeMusic(Track("a", "b"))
    now = [0.0]
    cached = CachedMusicProvider(inner, ttl_seconds=10, clock=lambda: now[0])
    cached.find("q"); cached.find("q")
    assert inner.calls == ["q"]
    now[0] = 11
    cached.find("q")
    assert inner.calls == ["q", "q"]


def test_cache_does_not_store_misses():
    inner = FakeMusic(None)
    cached = CachedMusicProvider(inner)
    cached.find("q"); cached.find("q")
    assert inner.calls == ["q", "q"]


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


def test_chain_with_local_never_silent():
    chain = FallbackChainMusicProvider([FakeMusic(error=OSError()), LocalMusicProvider()])
    assert chain.find("anything") is not None
