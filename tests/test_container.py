from reveil_musical.cli import main
from reveil_musical.container import build_wake_up_service
from reveil_musical.domain import Day, Weather
from tests.conftest import FakeHttp


def test_end_to_end_with_providers_down_still_wakes_up(capsys):
    service = build_wake_up_service(http=FakeHttp(error=ConnectionError("offline")))
    msg = service.wake_up("alice", Day.LUNDI, Weather.SOLEIL)
    assert msg.track.title == "Here Comes the Sun"  # fallback local
    assert "[EMAIL]" in capsys.readouterr().out


def test_end_to_end_with_itunes(capsys):
    http = FakeHttp({"results": [{"trackName": "Let It Snow", "artistName": "Dean Martin"}]})
    msg = build_wake_up_service(http=http).wake_up("bob", Day.DIMANCHE, Weather.NEIGE)
    assert msg.track.artist == "Dean Martin"
    assert "[SMS]" in capsys.readouterr().out


def test_cli_parses_and_runs(monkeypatch, capsys):
    import reveil_musical.cli as cli

    monkeypatch.setattr(cli, "build_wake_up_service", lambda: build_wake_up_service(http=FakeHttp(error=OSError())))
    main(["carol", "SAMEDI", "NUAGEUX"])
    assert "[PUSH] device-carol" in capsys.readouterr().out
