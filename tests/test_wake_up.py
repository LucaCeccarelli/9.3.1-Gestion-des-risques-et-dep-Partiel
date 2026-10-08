import pytest

from reveil_musical.domain import Channel, Day, Track, UnknownUser, UserPreferences, Weather
from reveil_musical.users import InMemoryUserPreferences
from reveil_musical.wake_up import WakeUpService
from tests.conftest import FakeMusic, FakeNotifier, FirstPicker


def make_service(prefs, music, notifier=None, picker=None):
    users = InMemoryUserPreferences({prefs.user_id: prefs})
    return WakeUpService(users, music, notifier or FakeNotifier(), picker or FirstPicker())


def test_candidates_mix_day_and_weather_choices(prefs):
    assert prefs.candidates(Day.DIMANCHE, Weather.SOLEIL) == [
        "Lazy Sunday", "Here Comes the Sun", "Walking on Sunshine",
    ]
    assert prefs.candidates(Day.LUNDI, Weather.SOLEIL) == ["Here Comes the Sun", "Walking on Sunshine"]
    assert prefs.candidates(Day.DIMANCHE, Weather.NEIGE) == ["Lazy Sunday"]
    assert prefs.candidates(Day.LUNDI, Weather.NEIGE) == ["Lovely Day"]  # secours


def test_picker_chooses_among_candidates(prefs):
    class LastPicker:
        def choice(self, options):
            return options[-1]

    music = FakeMusic(Track("Walking on Sunshine", "Katrina"))
    make_service(prefs, music, picker=LastPicker()).wake_up("u1", Day.MARDI, Weather.SOLEIL)
    assert music.calls == ["Walking on Sunshine"]


def test_wake_up_sends_message_on_preferred_channel(prefs):
    music = FakeMusic(Track("Here Comes the Sun", "The Beatles"))
    notifier = FakeNotifier()
    msg = make_service(prefs, music, notifier).wake_up("u1", Day.LUNDI, Weather.SOLEIL)
    assert music.calls == ["Here Comes the Sun"]
    assert notifier.sent[0].text == msg.text
    assert msg.channel == msg.delivered_via == Channel.SMS
    assert "Here Comes the Sun" in msg.text and "lundi" in msg.text


def test_uses_fallback_when_nothing_matches(prefs):
    music = FakeMusic(Track("Lovely Day", "Bill Withers"))
    make_service(prefs, music).wake_up("u1", Day.MARDI, Weather.NEIGE)
    assert music.calls == ["Lovely Day"]


def test_unknown_user(prefs):
    with pytest.raises(UnknownUser):
        make_service(prefs, FakeMusic()).wake_up("nobody", Day.LUNDI, Weather.SOLEIL)


def test_no_track_found_still_wakes_up_with_bare_title(prefs):
    msg = make_service(prefs, FakeMusic(None)).wake_up("u1", Day.LUNDI, Weather.SOLEIL)
    assert msg.track == Track("Here Comes the Sun", "artiste inconnu")


def test_degraded_delivery_is_reported(prefs):
    class DegradedNotifier:
        def send(self, message):
            return Channel.CONSOLE

    service = make_service(prefs, FakeMusic(Track("x", "y")), DegradedNotifier())
    msg = service.wake_up("u1", Day.LUNDI, Weather.SOLEIL)
    assert msg.channel == Channel.SMS and msg.delivered_via == Channel.CONSOLE


def test_empty_fallback_is_rejected_at_construction():
    with pytest.raises(ValueError):
        UserPreferences("x", tracks_by_weather={}, fallback_tracks=[], channel=Channel.EMAIL)
