from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger("developer_landing.contact")


@dataclass
class EmailResult:
    sent_via_smtp: bool
    owner_saved: bool
    user_saved: bool
    smtp_queued: bool = False


class EmailService:
    def send_contact_notifications(
        self,
        *,
        name: str,
        phone: str,
        email: str,
        comment: str,
        request_type: str | None,
        ai_reply: str | None,
        ai_available: bool,
    ) -> EmailResult:
        owner_body = self._owner_body(
            name=name,
            phone=phone,
            email=email,
            comment=comment,
            request_type=request_type,
            ai_available=ai_available,
        )
        user_body = self._user_body(
            name=name,
            comment=comment,
            ai_reply=ai_reply,
            ai_available=ai_available,
        )

        # Fast path for HTTP: save copies and return. SMTP goes to a background thread
        # so the contact form is not blocked by slow/blocked mail providers.
        owner_ok = self._save_to_file("owner", owner_body)
        user_ok = self._save_to_file("user", user_body)

        smtp_queued = False
        if self.is_configured():
            smtp_queued = True
            thread = threading.Thread(
                target=self._send_smtp_pair,
                kwargs={
                    "owner_subject": f"[Contact] Новое обращение от {name}",
                    "owner_body": owner_body,
                    "owner_to": [settings.CONTACT_OWNER_EMAIL],
                    "user_subject": "Мы получили ваше обращение",
                    "user_body": user_body,
                    "user_to": [email],
                },
                daemon=True,
                name="contact-smtp",
            )
            thread.start()
            logger.info(
                "SMTP queued in background (owner=%s user=%s)",
                settings.CONTACT_OWNER_EMAIL,
                email,
            )

        return EmailResult(
            sent_via_smtp=False,
            owner_saved=owner_ok,
            user_saved=user_ok,
            smtp_queued=smtp_queued,
        )

    def is_configured(self) -> bool:
        return bool(
            settings.EMAIL_HOST
            and settings.EMAIL_HOST_USER
            and settings.EMAIL_HOST_PASSWORD
            and settings.CONTACT_OWNER_EMAIL
        )

    def _smtp_configured(self) -> bool:
        return self.is_configured()

    def _send_smtp_pair(
        self,
        *,
        owner_subject: str,
        owner_body: str,
        owner_to: list[str],
        user_subject: str,
        user_body: str,
        user_to: list[str],
    ) -> None:
        try:
            self._send_smtp(subject=owner_subject, body=owner_body, to=owner_to)
            self._send_smtp(subject=user_subject, body=user_body, to=user_to)
            logger.info("SMTP background send OK to %s and %s", owner_to, user_to)
        except Exception:
            logger.exception("SMTP background send failed")

    def _send_smtp(self, *, subject: str, body: str, to: list[str]) -> None:
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
        )
        message.send(fail_silently=False)

    def _save_to_file(self, prefix: str, body: str) -> bool:
        try:
            directory: Path = settings.STORAGE_MAIL_DIR
            directory.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = directory / f"{prefix}_{stamp}.txt"
            path.write_text(body, encoding="utf-8")
            return True
        except OSError:
            logger.exception("Failed to write mail fallback file")
            return False

    def _owner_body(
        self,
        *,
        name: str,
        phone: str,
        email: str,
        comment: str,
        request_type: str | None,
        ai_available: bool,
    ) -> str:
        return (
            "Новое обращение с лендинга\n\n"
            f"Имя: {name}\n"
            f"Телефон: {phone}\n"
            f"Email: {email}\n"
            f"Тип (AI): {request_type or 'n/a'}\n"
            f"AI available: {ai_available}\n\n"
            f"Комментарий:\n{comment}\n"
        )

    def _user_body(
        self,
        *,
        name: str,
        comment: str,
        ai_reply: str | None,
        ai_available: bool,
    ) -> str:
        reply = ai_reply if ai_available and ai_reply else (
            "Спасибо за обращение! Мы получили ваше сообщение и ответим в ближайшее время."
        )
        return (
            f"Здравствуйте, {name}!\n\n"
            f"{reply}\n\n"
            "---\n"
            "Ваше сообщение:\n"
            f"{comment}\n"
        )
