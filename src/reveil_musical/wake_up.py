"""Cas d'usage (Facade) : déclencher le réveil d'un utilisateur. Ne dépend que des ports."""

from reveil_musical.domain import (
    Day,
    MusicProvider,
    Notifier,
    UserPreferencesProvider,
    WakeUpMessage,
    Weather,
)


class WakeUpService:
    def __init__(
        self,
        users: UserPreferencesProvider,
        music: MusicProvider,
        notifier: Notifier,
    ) -> None:
        self._users = users
        self._music = music
        self._notifier = notifier

    def wake_up(self, user_id: str, day: Day, weather: Weather) -> WakeUpMessage:
        prefs = self._users.get(user_id)
        query = prefs.tracks_by_weather.get(weather, prefs.fallback_track)
        track = self._music.find(query)
        if track is None:  # le fournisseur injecté doit garantir un morceau
            raise RuntimeError(f"Aucun morceau trouvé pour « {query} »")
        message = WakeUpMessage(user_id, prefs.channel, day, weather, track)
        self._notifier.send(message)
        return message
