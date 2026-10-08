"""Fournisseur de dernier recours : liste codée en dur, sans réseau. Ne tombe jamais en panne."""

from reveil_musical.domain import Track

LOCAL_TRACKS = (
    Track("Here Comes the Sun", "The Beatles"),
    Track("Lovely Day", "Bill Withers"),
    Track("Wake Me Up Before You Go-Go", "Wham!"),
    Track("Good Morning", "Gene Kelly"),
)


class LocalMusicProvider:
    def __init__(self, tracks: tuple[Track, ...] = LOCAL_TRACKS) -> None:
        self._tracks = tracks

    def find(self, query: str) -> Track | None:
        """Complète l'artiste si le titre est dans la liste ; sinon None : le cas d'usage garde
        le titre choisi par l'utilisateur plutôt que de lui imposer un autre morceau."""
        wanted = query.casefold()
        return next((t for t in self._tracks if wanted in t.title.casefold()), None)
