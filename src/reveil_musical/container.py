"""Racine de composition : conteneur d'injection de dépendances (dependency-injector).

Seul endroit où les implémentations concrètes sont assemblées. Les tests remplacent un
fournisseur avec `container.<provider>.override(...)`.
"""

from dependency_injector import containers, providers

from reveil_musical.domain import Channel
from reveil_musical.music.http import UrllibHttpClient
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


class Container(containers.DeclarativeContainer):
    http = providers.Singleton(UrllibHttpClient)

    # Musique : fournisseurs interchangeables, chaînés, le local en dernier recours.
    itunes = providers.Singleton(CachedMusicProvider, providers.Singleton(ITunesMusicProvider, http))
    musicbrainz = providers.Singleton(
        CachedMusicProvider, providers.Singleton(MusicBrainzMusicProvider, http, USER_AGENT)
    )
    local = providers.Singleton(LocalMusicProvider)
    music = providers.Singleton(FallbackChainMusicProvider, providers.List(itunes, musicbrainz, local))

    # Notification : un adaptateur par canal, routés avec bascule en cas de panne.
    notifier = providers.Singleton(
        ChannelRouter,
        providers.Dict(
            {
                Channel.EMAIL: providers.Singleton(EmailNotifier, providers.Singleton(EmailMock)),
                Channel.SMS: providers.Singleton(SmsNotifier, providers.Singleton(SmsMock)),
                Channel.PUSH: providers.Singleton(PushNotifier, providers.Singleton(PushMock)),
            }
        ),
    )

    users = providers.Singleton(InMemoryUserPreferences, DEMO_USERS)

    wake_up_service = providers.Singleton(WakeUpService, users=users, music=music, notifier=notifier)
