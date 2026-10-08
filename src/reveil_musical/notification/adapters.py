"""Adaptateurs (pattern Adapter) : ramènent chaque mock vers le port Notifier."""

from reveil_musical.domain import Channel, WakeUpMessage
from reveil_musical.notification.mocks import EmailMock, PushMock, SmsMock


class EmailNotifier:
    def __init__(self, email: EmailMock) -> None:
        self._email = email

    def send(self, message: WakeUpMessage) -> Channel:
        self._email.send_mail(
            to=f"{message.user_id}@reveil-musical.local",
            subject=f"Réveil musical — {message.day.value.capitalize()}",
            body=message.text,
        )
        return Channel.EMAIL


class SmsNotifier:
    def __init__(self, sms: SmsMock) -> None:
        self._sms = sms

    def send(self, message: WakeUpMessage) -> Channel:
        text = message.text[:160]
        if not self._sms.push_sms(f"+33-{message.user_id}", text):
            raise RuntimeError("SMS refusé")
        return Channel.SMS


class PushNotifier:
    def __init__(self, push: PushMock) -> None:
        self._push = push

    def send(self, message: WakeUpMessage) -> Channel:
        result = self._push.notify(
            f"device-{message.user_id}",
            {"title": "Réveil musical", "body": message.text},
        )
        if result.get("status") != "queued":
            raise RuntimeError(f"push refusé : {result}")
        return Channel.PUSH
