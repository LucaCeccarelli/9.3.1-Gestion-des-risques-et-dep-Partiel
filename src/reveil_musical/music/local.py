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
        if not tracks:
            raise ValueError("au moins un morceau local requis")
        self._tracks = tracks

    def find(self, query: str) -> Track:
        """Le morceau demandé s'il est dans la liste, sinon le premier de la liste : jamais de silence."""
        # ponytail: toujours le premier morceau en secours ; tirage au sort si la monotonie gêne
        wanted = query.casefold()
        return next((t for t in self._tracks if wanted in t.title.casefold()), self._tracks[0])
