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
            Weather.SOLEIL: "Here Comes the Sun",
            Weather.PLUIE: "Riders on the Storm",
        },
        fallback_track="Lovely Day",
        channel=Channel.EMAIL,
        tracks_by_day={Day.DIMANCHE: "Lazy Sunday"},
    ),
    "bob": UserPreferences(
        user_id="bob",
        tracks_by_weather={Weather.NEIGE: "Let It Snow"},
        fallback_track="Wake Me Up",
        channel=Channel.SMS,
        tracks_by_day={Day.LUNDI: "Manic Monday"},
    ),
    "carol": UserPreferences(
        user_id="carol",
        tracks_by_weather={Weather.NUAGEUX: "Cloudbusting"},
        fallback_track="Good Morning",
        channel=Channel.PUSH,
    ),
}
