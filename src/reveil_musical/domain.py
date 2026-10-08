"""Modèle métier et ports (interfaces). Aucun détail technique ici."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Protocol, Sequence


class Weather(StrEnum):
    SOLEIL = "SOLEIL"
    PLUIE = "PLUIE"
    NEIGE = "NEIGE"
    NUAGEUX = "NUAGEUX"


class Day(StrEnum):
    LUNDI = "LUNDI"
    MARDI = "MARDI"
    MERCREDI = "MERCREDI"
    JEUDI = "JEUDI"
    VENDREDI = "VENDREDI"
    SAMEDI = "SAMEDI"
    DIMANCHE = "DIMANCHE"


class Channel(StrEnum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"


@dataclass(frozen=True)
class Track:
    title: str
    artist: str


@dataclass(frozen=True)
class UserPreferences:
    user_id: str
    tracks_by_weather: Mapping[Weather, Sequence[str]]  # météo -> morceaux souhaités
    fallback_tracks: Sequence[str]  # morceaux de secours pour les cas non couverts
    channel: Channel
    tracks_by_day: Mapping[Day, Sequence[str]] = field(default_factory=dict)  # jour -> morceaux

    def __post_init__(self) -> None:
        if not self.fallback_tracks:  # garantit candidates() non vide : jamais de silence
            raise ValueError(f"{self.user_id} : au moins un morceau de secours requis")

    def candidates(self, day: Day, weather: Weather) -> list[str]:
        """Morceaux possibles : ceux du jour et ceux de la météo réunis, sinon les secours."""
        pool = [*self.tracks_by_day.get(day, ()), *self.tracks_by_weather.get(weather, ())]
        return list(dict.fromkeys(pool or self.fallback_tracks))


@dataclass(frozen=True)
class WakeUpMessage:
    user_id: str
    channel: Channel
    day: Day
    weather: Weather
    track: Track

    @property
    def text(self) -> str:
        return (
            f"Bonjour, c'est {self.day.value.lower()} et il fait {self.weather.value.lower()} : "
            f"réveil avec « {self.track.title} » de {self.track.artist}."
        )


# --- Ports -----------------------------------------------------------------


class UserPreferencesProvider(Protocol):
    def get(self, user_id: str) -> UserPreferences: ...


class TrackPicker(Protocol):
    def choice(self, options: Sequence[str]) -> str:
        """Choisit un morceau parmi les candidats (random.Random convient)."""
        ...


class MusicProvider(Protocol):
    def find(self, query: str) -> Track | None:
        """Retourne le morceau trouvé, None si inconnu. Peut lever en cas de panne."""
        ...


class Notifier(Protocol):
    def send(self, message: WakeUpMessage) -> None:
        """Envoie le message. Lève en cas de panne du canal."""
        ...
