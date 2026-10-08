from fastapi.testclient import TestClient

from reveil_musical.api import create_app
from reveil_musical.container import Container
from reveil_musical.domain import Channel
from reveil_musical.notification.router import ChannelRouter
from tests.conftest import FakeHttp, FakeNotifier, FirstPicker


def client(http=None, **overrides):
    container = Container()
    container.http.override(http or FakeHttp(error=ConnectionError("offline")))
    container.picker.override(FirstPicker())
    for name, value in overrides.items():
        getattr(container, name).override(value)
    return TestClient(create_app(container))


def test_wake_up_endpoint_degrades_to_local_track(capsys):
    r = client().post("/wake-up", json={"user_id": "alice", "day": "MARDI", "weather": "SOLEIL"})
    assert r.status_code == 200
    body = r.json()
    assert body["track_title"] == "Here Comes the Sun" and body["channel"] == "EMAIL"
    assert "[EMAIL]" in capsys.readouterr().out


def test_wake_up_endpoint_with_itunes():
    http = FakeHttp({"results": [{"trackName": "Let It Snow", "artistName": "Dean Martin"}]})
    r = client(http).post("/wake-up", json={"user_id": "bob", "day": "DIMANCHE", "weather": "NEIGE"})
    assert r.json()["track_artist"] == "Dean Martin"


def test_unknown_user_is_404():
    r = client().post("/wake-up", json={"user_id": "nobody", "day": "LUNDI", "weather": "SOLEIL"})
    assert r.status_code == 404


def test_invalid_weather_is_422():
    r = client().post("/wake-up", json={"user_id": "alice", "day": "LUNDI", "weather": "GRELE"})
    assert r.status_code == 422


def test_all_channels_down_is_503():
    only_dead_email = ChannelRouter({Channel.EMAIL: FakeNotifier(error=OSError("down"))})
    r = client(notifier=only_dead_email).post(
        "/wake-up", json={"user_id": "alice", "day": "LUNDI", "weather": "SOLEIL"}
    )
    assert r.status_code == 503
