from reveil_musical.cli import main
from reveil_musical.container import Container
from reveil_musical.domain import Day, Weather
from tests.conftest import FakeHttp


def container_with(http):
    container = Container()
    container.http.override(http)
    return container


def test_end_to_end_with_providers_down_still_wakes_up(capsys):
    service = container_with(FakeHttp(error=ConnectionError("offline"))).wake_up_service()
    msg = service.wake_up("alice", Day.LUNDI, Weather.SOLEIL)
    assert msg.track.title == "Here Comes the Sun"  # fallback local
    assert "[EMAIL]" in capsys.readouterr().out


def test_end_to_end_with_itunes(capsys):
    http = FakeHttp({"results": [{"trackName": "Let It Snow", "artistName": "Dean Martin"}]})
    msg = container_with(http).wake_up_service().wake_up("bob", Day.DIMANCHE, Weather.NEIGE)
    assert msg.track.artist == "Dean Martin"
    assert "[SMS]" in capsys.readouterr().out


def test_any_provider_can_be_swapped_without_touching_the_rest(capsys):
    container = Container()
    container.music.override(container.local())  # un autre fournisseur, même port
    msg = container.wake_up_service().wake_up("carol", Day.JEUDI, Weather.PLUIE)
    assert msg.track.title == "Good Morning"


def test_cli_parses_and_runs(monkeypatch, capsys):
    import reveil_musical.cli as cli

    monkeypatch.setattr(cli, "Container", lambda: container_with(FakeHttp(error=OSError())))
    main(["carol", "SAMEDI", "NUAGEUX"])
    assert "[PUSH] device-carol" in capsys.readouterr().out
