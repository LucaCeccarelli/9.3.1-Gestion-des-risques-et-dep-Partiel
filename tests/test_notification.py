import pytest

from reveil_musical.domain import Channel
from reveil_musical.notification.adapters import EmailNotifier, PushNotifier, SmsNotifier
from reveil_musical.notification.mocks import EmailMock, PushMock, SmsMock
from reveil_musical.notification.router import ChannelRouter, ConsoleNotifier
from tests.conftest import FakeNotifier


def test_email_adapter(message, capsys):
    EmailNotifier(EmailMock()).send(message)
    out = capsys.readouterr().out
    assert "[EMAIL] to=u1@reveil-musical.local" in out and "Lovely Day" in out


def test_sms_adapter(message, capsys):
    SmsNotifier(SmsMock()).send(message)
    assert "[SMS] +33-u1" in capsys.readouterr().out


def test_sms_adapter_raises_when_refused(message):
    class RefusingSms(SmsMock):
        def push_sms(self, phone_number, text):
            return False

    with pytest.raises(RuntimeError):
        SmsNotifier(RefusingSms()).send(message)


def test_push_adapter(message, capsys):
    PushNotifier(PushMock()).send(message)
    assert "[PUSH] device-u1" in capsys.readouterr().out


def test_push_adapter_raises_when_not_queued(message):
    class RefusingPush(PushMock):
        def notify(self, device_token, payload):
            return {"status": "error"}

    with pytest.raises(RuntimeError):
        PushNotifier(RefusingPush()).send(message)


def test_router_uses_preferred_channel(message):
    sms, email = FakeNotifier(), FakeNotifier()
    used = ChannelRouter({Channel.EMAIL: email, Channel.SMS: sms}, FakeNotifier()).send(message)
    assert used == Channel.SMS
    assert sms.sent == [message] and email.sent == []


def test_router_degrades_to_other_channel(message, caplog):
    sms, email = FakeNotifier(error=TimeoutError("down")), FakeNotifier()
    used = ChannelRouter({Channel.EMAIL: email, Channel.SMS: sms}, FakeNotifier()).send(message)
    assert used == Channel.EMAIL and email.sent == [message]
    assert "mode dégradé" in caplog.text


def test_router_falls_back_to_last_resort_when_all_down(message, caplog):
    last = FakeNotifier()
    ChannelRouter({Channel.SMS: FakeNotifier(error=OSError("x"))}, last).send(message)
    assert last.sent == [message]
    assert "dernier recours" in caplog.text


def test_console_notifier_prints(message, capsys):
    assert ConsoleNotifier().send(message) == Channel.CONSOLE
    assert message.text in capsys.readouterr().out


def test_router_without_preferred_channel_configured(message):
    email = FakeNotifier()
    ChannelRouter({Channel.EMAIL: email}, FakeNotifier()).send(message)  # préférence SMS absente
    assert email.sent == [message]


def test_router_requires_channels():
    with pytest.raises(ValueError):
        ChannelRouter({}, FakeNotifier())
