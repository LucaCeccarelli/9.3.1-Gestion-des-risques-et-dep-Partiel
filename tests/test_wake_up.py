import pytest

from reveil_musical.domain import Channel, Day, Track, Weather
from reveil_musical.users import InMemoryUserPreferences, UnknownUser
from reveil_musical.wake_up import WakeUpService
from tests.conftest import FakeMusic, FakeNotifier


def make_service(prefs, music, notifier=None):
    return WakeUpService(InMemoryUserPreferences({prefs.user_id: prefs}), music, notifier or FakeNotifier())


def test_uses_track_chosen_for_weather(prefs):
    music = FakeMusic(Track("Here Comes the Sun", "The Beatles"))
    notifier = FakeNotifier()
    msg = make_service(prefs, music, notifier).wake_up("u1", Day.LUNDI, Weather.SOLEIL)
    assert music.calls == ["Here Comes the Sun"]
    assert notifier.sent == [msg]
    assert msg.channel == Channel.SMS
    assert "Here Comes the Sun" in msg.text and "lundi" in msg.text


def test_uses_fallback_track_for_uncovered_weather(prefs):
    music = FakeMusic(Track("Lovely Day", "Bill Withers"))
    make_service(prefs, music).wake_up("u1", Day.MARDI, Weather.NEIGE)
    assert music.calls == ["Lovely Day"]


def test_unknown_user(prefs):
    with pytest.raises(UnknownUser):
        make_service(prefs, FakeMusic()).wake_up("nobody", Day.LUNDI, Weather.SOLEIL)


def test_no_track_is_an_error(prefs):
    with pytest.raises(RuntimeError):
        make_service(prefs, FakeMusic(None)).wake_up("u1", Day.LUNDI, Weather.SOLEIL)
