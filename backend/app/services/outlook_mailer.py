from email.message import EmailMessage
import smtplib

from app.core.config import get_settings


class OutlookMailer:
    def __init__(self) -> None:
        settings = get_settings()
        self._host = settings.outlook_smtp_host
        self._port = settings.outlook_smtp_port
        self._username = settings.outlook_smtp_username
        self._password = settings.outlook_smtp_password
        self._from_email = settings.outlook_from_email or settings.outlook_smtp_username

    def is_configured(self) -> bool:
        return bool(self._host and self._port and self._username and self._password and self._from_email)

    def send_post_notification(self, to_email: str, subject: str, body: str) -> None:
        if not self.is_configured():
            raise ValueError("Outlook SMTP settings are missing. Configure outlook_smtp_username/password in backend/.env")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._from_email
        message["To"] = to_email
        message.set_content(body)

        with smtplib.SMTP(self._host, self._port, timeout=20) as client:
            client.starttls()
            client.login(self._username, self._password)
            client.send_message(message)
