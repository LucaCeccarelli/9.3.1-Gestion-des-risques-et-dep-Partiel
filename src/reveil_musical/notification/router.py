"""Chain of Responsibility sur les canaux : préféré d'abord, sinon bascule (mode dégradé),
en dernier recours la console : le silence n'est jamais acceptable."""

import logging
from collections.abc import Mapping

from reveil_musical.domain import Channel, Notifier, WakeUpMessage

log = logging.getLogger(__name__)


class ConsoleNotifier:
    """Dernier recours : ne dépend de rien, ne tombe jamais."""

    def send(self, message: WakeUpMessage) -> Channel:
        print(f"[CONSOLE] {message.user_id}: {message.text}")
        return Channel.FALLBACK


class ChannelRouter:
    def __init__(self, notifiers: Mapping[Channel, Notifier], last_resort: Notifier) -> None:
        if not notifiers:
            raise ValueError("au moins un canal requis")
        self._notifiers = notifiers
        self._last_resort = last_resort

    def send(self, message: WakeUpMessage) -> Channel:
        order = [message.channel] + [c for c in self._notifiers if c != message.channel]
        for channel in order:
            notifier = self._notifiers.get(channel)
            if notifier is None or channel not in message.contacts:
                continue
            try:
                used = notifier.send(message)
                if used != message.channel:
                    log.warning("mode dégradé : %s envoyé via %s", message.user_id, used)
                return used
            except Exception as exc:  # noqa: BLE001 — panne du canal => suivant
                log.warning("canal %s en panne : %s", channel, exc)
        log.error("tous les canaux en panne : %s envoyé via le dernier recours", message.user_id)
        return self._last_resort.send(message)
