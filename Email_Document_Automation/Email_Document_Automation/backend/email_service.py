from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .config import get_settings


def smtp_configured() -> bool:
    settings = get_settings()
    return bool(settings.smtp_host and settings.smtp_from_email and settings.smtp_username)


def send_email(to_email: str, subject: str, body: str) -> dict:
    settings = get_settings()
    if not smtp_configured():
        raise RuntimeError(
            "SMTP is not configured. Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, "
            "and SMTP_FROM_EMAIL in .env to enable email sending."
        )

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)

    return {"sent": True, "to": to_email, "subject": subject}
