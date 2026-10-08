from reveil_musical.container import Container
from reveil_musical.domain import Day, Weather
from tests.conftest import FakeHttp


def test_container_builds_working_service(capsys):
    container = Container()
    container.http.override(FakeHttp(error=ConnectionError("offline")))
    msg = container.wake_up_service().wake_up("alice", Day.LUNDI, Weather.SOLEIL)
    assert msg.track.title == "Here Comes the Sun"  # fallback local
    assert "[EMAIL]" in capsys.readouterr().out


def test_any_provider_can_be_swapped_without_touching_the_rest():
    container = Container()
    container.music.override(container.local())  # un autre fournisseur, même port
    msg = container.wake_up_service().wake_up("carol", Day.JEUDI, Weather.PLUIE)
    assert msg.track.title == "Good Morning"
