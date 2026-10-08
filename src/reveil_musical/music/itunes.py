"""Fournisseur musical : iTunes Search API."""

from urllib.parse import urlencode

from reveil_musical.domain import Track
from reveil_musical.music.http import HttpClient

SEARCH_URL = "https://itunes.apple.com/search"


class ITunesMusicProvider:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def find(self, query: str) -> Track | None:
        url = f"{SEARCH_URL}?{urlencode({'term': query, 'media': 'music', 'limit': 5})}"
        results = self._http.get_json(url).get("results", [])
        for item in results:
            if item.get("trackName") and item.get("artistName"):
                # trackViewUrl volontairement ignoré : détail iTunes, pas métier.
                return Track(title=item["trackName"], artist=item["artistName"])
        return None
