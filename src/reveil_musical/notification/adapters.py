"""Adaptateurs (pattern Adapter) : ramènent chaque mock vers le port Notifier."""

from reveil_musical.domain import Channel, WakeUpMessage
from reveil_musical.notification.mocks import EmailMock, PushMock, SmsMock


class EmailNotifier:
    def __init__(self, email: EmailMock) -> None:
        self._email = email

    def send(self, message: WakeUpMessage) -> Channel:
        self._email.send_mail(
            to=message.contacts[Channel.EMAIL],
            subject=f"Réveil musical — {message.day.value.capitalize()}",
            body=message.text,
        )
        return Channel.EMAIL


class SmsNotifier:
    def __init__(self, sms: SmsMock) -> None:
        self._sms = sms

    def send(self, message: WakeUpMessage) -> Channel:
        if not self._sms.push_sms(message.contacts[Channel.SMS], message.text):
            raise RuntimeError("SMS refusé (texte trop long ?)")
        return Channel.SMS


class PushNotifier:
    def __init__(self, push: PushMock) -> None:
        self._push = push

    def send(self, message: WakeUpMessage) -> Channel:
        result = self._push.notify(
            message.contacts[Channel.PUSH],
            {"title": "Réveil musical", "body": message.text},
        )
        if result.get("status") != "queued":
            raise RuntimeError(f"push refusé : {result}")
        return Channel.PUSH
