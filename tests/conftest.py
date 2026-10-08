import pytest

from reveil_musical.domain import Channel, Day, Track, UserPreferences, WakeUpMessage, Weather


class FakeMusic:
    def __init__(self, track=None, error=None):
        self.track, self.error, self.calls = track, error, []

    def find(self, query):
        self.calls.append(query)
        if self.error:
            raise self.error
        return self.track


class FakeNotifier:
    def __init__(self, error=None):
        self.error, self.sent = error, []

    def send(self, message):
        if self.error:
            raise self.error
        self.sent.append(message)
        return message.channel


class FirstPicker:
    def choice(self, options):
        return options[0]


class FakeHttp:
    def __init__(self, payload=None, error=None):
        self.payload, self.error, self.requests = payload, error, []

    def get_json(self, url, headers=None):
        self.requests.append((url, dict(headers or {})))
        if self.error:
            raise self.error
        return self.payload


@pytest.fixture
def prefs():
    return UserPreferences(
        user_id="u1",
        tracks_by_weather={Weather.SOLEIL: ["Here Comes the Sun", "Walking on Sunshine"]},
        tracks_by_day={Day.DIMANCHE: ["Lazy Sunday"]},
        fallback_tracks=["Lovely Day"],
        channel=Channel.SMS,
    )


@pytest.fixture
def message():
    return WakeUpMessage("u1", Channel.SMS, Day.LUNDI, Weather.PLUIE, Track("Lovely Day", "Bill Withers"))
