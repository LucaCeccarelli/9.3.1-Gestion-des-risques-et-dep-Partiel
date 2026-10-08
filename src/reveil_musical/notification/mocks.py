"""Mocks des canaux, chacun avec une interface volontairement différente.

Aucun envoi réel : écriture console.
"""


class EmailMock:
    def send_mail(self, to: str, subject: str, body: str) -> None:
        print(f"[EMAIL] to={to} subject={subject!r}\n{body}")


class SmsMock:
    def push_sms(self, phone_number: str, text: str) -> bool:
        if len(text) > 160:
            return False
        print(f"[SMS] {phone_number}: {text}")
        return True


class PushMock:
    def notify(self, device_token: str, payload: dict[str, str]) -> dict[str, str]:
        print(f"[PUSH] {device_token} {payload}")
        return {"status": "queued", "device": device_token}
