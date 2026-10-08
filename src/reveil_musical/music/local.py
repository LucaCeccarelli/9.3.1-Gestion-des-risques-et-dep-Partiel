"""Fournisseur de dernier recours : liste codée en dur. Ne tombe jamais en panne."""

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

    def find(self, query: str) -> Track:
        wanted = query.casefold()
        for track in self._tracks:
            if wanted in track.title.casefold():
                return track
        # ponytail: choix déterministe par hash de la requête ; aléatoire pondéré si besoin
        return self._tracks[sum(map(ord, query)) % len(self._tracks)]
