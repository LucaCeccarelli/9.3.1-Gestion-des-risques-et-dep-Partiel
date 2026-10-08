"""Racine de composition : conteneur d'injection de dépendances (dependency-injector).

Seul endroit où les implémentations concrètes sont assemblées. Les tests remplacent un
fournisseur avec `container.<provider>.override(...)`.
"""

import random

from dependency_injector import containers, providers

from reveil_musical.domain import Channel
from reveil_musical.music.http import UrllibHttpClient
from reveil_musical.music.itunes import ITunesMusicProvider
from reveil_musical.music.local import LocalMusicProvider
from reveil_musical.music.musicbrainz import MusicBrainzMusicProvider
from reveil_musical.music.resilient import (
    CachedMusicProvider,
    FallbackChainMusicProvider,
    RateLimitedMusicProvider,
)
from reveil_musical.notification.adapters import EmailNotifier, PushNotifier, SmsNotifier
from reveil_musical.notification.mocks import EmailMock, PushMock, SmsMock
from reveil_musical.notification.router import ChannelRouter, ConsoleNotifier
from reveil_musical.users import DEMO_USERS, InMemoryUserPreferences
from reveil_musical.wake_up import WakeUpService

USER_AGENT = "ReveilMusical/0.1 (luca.ceccarelli@etu.mines-ales.fr)"


class Container(containers.DeclarativeContainer):
    http = providers.Singleton(UrllibHttpClient)

    # Musique : fournisseurs interchangeables, chaînés, le local en dernier recours.
    # Chaque API distante est décorée : cache (même titre -> un appel/h) puis quota de l'API.
    itunes = providers.Singleton(
        CachedMusicProvider,
        providers.Singleton(
            RateLimitedMusicProvider,
            providers.Singleton(ITunesMusicProvider, http),
            max_calls=20,
            period=60,
        ),
    )
    musicbrainz = providers.Singleton(
        CachedMusicProvider,
        providers.Singleton(
            RateLimitedMusicProvider,
            providers.Singleton(MusicBrainzMusicProvider, http, USER_AGENT),
            max_calls=1,
            period=1,
        ),
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
        last_resort=providers.Singleton(ConsoleNotifier),
    )

    users = providers.Singleton(InMemoryUserPreferences, DEMO_USERS)
    picker = providers.Singleton(random.Random)

    wake_up_service = providers.Singleton(
        WakeUpService, users=users, music=music, notifier=notifier, picker=picker
    )
