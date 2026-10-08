"""Fournisseur musical : MusicBrainz."""

from urllib.parse import urlencode

from reveil_musical.domain import Track
from reveil_musical.music.http import HttpClient

SEARCH_URL = "https://musicbrainz.org/ws/2/recording"


class MusicBrainzMusicProvider:
    def __init__(self, http: HttpClient, user_agent: str) -> None:
        self._http = http
        self._headers = {"User-Agent": user_agent, "Accept": "application/json"}

    def find(self, query: str) -> Track | None:
        url = f"{SEARCH_URL}?{urlencode({'query': query, 'fmt': 'json', 'limit': 5})}"
        recordings = self._http.get_json(url, self._headers).get("recordings", [])
        for item in recordings:
            artist = "".join(
                credit.get("name", "") + credit.get("joinphrase", "")
                for credit in item.get("artist-credit", [])
            )
            if item.get("title") and artist:
                return Track(title=item["title"], artist=artist)
        return None
