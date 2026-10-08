"""Mock du service interne de préférences utilisateur."""

from reveil_musical.domain import Channel, Day, UserPreferences, Weather


class UnknownUser(LookupError):
    pass


class InMemoryUserPreferences:
    def __init__(self, users: dict[str, UserPreferences]) -> None:
        self._users = users

    def get(self, user_id: str) -> UserPreferences:
        try:
            return self._users[user_id]
        except KeyError:
            raise UnknownUser(user_id) from None


DEMO_USERS = {
    "alice": UserPreferences(
        user_id="alice",
        tracks_by_weather={
            Weather.SOLEIL: ["Here Comes the Sun", "Walking on Sunshine"],
            Weather.PLUIE: ["Riders on the Storm", "Purple Rain"],
        },
        tracks_by_day={
            Day.LUNDI: ["I Don't Like Mondays"],
            Day.DIMANCHE: ["Lazy Sunday", "Sunday Morning"],
        },
        fallback_tracks=["Lovely Day"],
        channel=Channel.EMAIL,
    ),
    "bob": UserPreferences(
        user_id="bob",
        tracks_by_weather={Weather.NEIGE: ["Let It Snow", "Snow (Hey Oh)"]},
        tracks_by_day={Day.LUNDI: ["Manic Monday", "Blue Monday"], Day.VENDREDI: ["Friday I'm in Love"]},
        fallback_tracks=["Wake Me Up", "Good Morning"],
        channel=Channel.SMS,
    ),
    "carol": UserPreferences(
        user_id="carol",
        tracks_by_weather={Weather.NUAGEUX: ["Cloudbusting"]},
        fallback_tracks=["Good Morning"],
        channel=Channel.PUSH,
    ),
}
