"""Racine de composition (Factory) : seul endroit où les implémentations concrètes sont assemblées."""

from reveil_musical.domain import Channel
from reveil_musical.music.http import HttpClient, UrllibHttpClient
from reveil_musical.music.itunes import ITunesMusicProvider
from reveil_musical.music.local import LocalMusicProvider
from reveil_musical.music.musicbrainz import MusicBrainzMusicProvider
from reveil_musical.music.resilient import CachedMusicProvider, FallbackChainMusicProvider
from reveil_musical.notification.adapters import EmailNotifier, PushNotifier, SmsNotifier
from reveil_musical.notification.mocks import EmailMock, PushMock, SmsMock
from reveil_musical.notification.router import ChannelRouter
from reveil_musical.users import DEMO_USERS, InMemoryUserPreferences
from reveil_musical.wake_up import WakeUpService

USER_AGENT = "ReveilMusical/0.1 (contact@reveil-musical.local)"


def build_wake_up_service(http: HttpClient | None = None) -> WakeUpService:
    http = http or UrllibHttpClient()
    music = FallbackChainMusicProvider(
        [
            CachedMusicProvider(ITunesMusicProvider(http)),
            CachedMusicProvider(MusicBrainzMusicProvider(http, USER_AGENT)),
            LocalMusicProvider(),
        ]
    )
    notifier = ChannelRouter(
        {
            Channel.EMAIL: EmailNotifier(EmailMock()),
            Channel.SMS: SmsNotifier(SmsMock()),
            Channel.PUSH: PushNotifier(PushMock()),
        }
    )
    return WakeUpService(InMemoryUserPreferences(DEMO_USERS), music, notifier)
