"""Chain of Responsibility sur les canaux : préféré d'abord, sinon bascule (mode dégradé)."""

import logging
from collections.abc import Mapping

from reveil_musical.domain import Channel, Notifier, WakeUpMessage

log = logging.getLogger(__name__)


class AllChannelsFailed(RuntimeError):
    pass


class ChannelRouter:
    def __init__(self, notifiers: Mapping[Channel, Notifier]) -> None:
        if not notifiers:
            raise ValueError("au moins un canal requis")
        self._notifiers = notifiers

    def send(self, message: WakeUpMessage) -> None:
        order = [message.channel] + [c for c in self._notifiers if c != message.channel]
        errors: list[str] = []
        for channel in order:
            notifier = self._notifiers.get(channel)
            if notifier is None:
                continue
            try:
                notifier.send(message)
                if channel != message.channel:
                    log.warning("mode dégradé : %s envoyé via %s", message.user_id, channel)
                return
            except Exception as exc:  # noqa: BLE001 — panne du canal => suivant
                log.warning("canal %s en panne : %s", channel, exc)
                errors.append(f"{channel}: {exc}")
        raise AllChannelsFailed("; ".join(errors))
