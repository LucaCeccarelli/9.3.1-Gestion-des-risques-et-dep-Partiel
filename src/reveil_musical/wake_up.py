"""Cas d'usage (Facade) : déclencher le réveil d'un utilisateur. Ne dépend que des ports."""

from dataclasses import replace

from reveil_musical.domain import (
    Day,
    MusicProvider,
    Notifier,
    Track,
    TrackPicker,
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
        picker: TrackPicker,
    ) -> None:
        self._users = users
        self._music = music
        self._notifier = notifier
        self._picker = picker

    def wake_up(self, user_id: str, day: Day, weather: Weather) -> WakeUpMessage:
        prefs = self._users.get(user_id)
        query = self._picker.choice(prefs.candidates(day, weather))
        # Jamais de silence, même sans fournisseur local en bout de chaîne : le titre choisi suffit.
        track = self._music.find(query) or Track(query, "artiste inconnu")
        message = WakeUpMessage(user_id, prefs.channel, day, weather, track, prefs.contacts)
        return replace(message, delivered_via=self._notifier.send(message))
