from __future__ import annotations

import logging
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

        owner_ok = self._save_to_file("owner", owner_body)
        user_ok = self._save_to_file("user", user_body)

        sent_via_smtp = False
        if self.is_configured():
            try:
                self._send_smtp(
                    subject=f"[Contact] Новое обращение от {name}",
                    body=owner_body,
                    to=[settings.CONTACT_OWNER_EMAIL],
                )
                self._send_smtp(
                    subject="Мы получили ваше обращение",
                    body=user_body,
                    to=[email],
                )
                sent_via_smtp = True
                logger.info(
                    "SMTP sent OK to owner=%s user=%s",
                    settings.CONTACT_OWNER_EMAIL,
                    email,
                )
            except Exception:
                logger.exception("SMTP send failed, file copies already saved")

        return EmailResult(
            sent_via_smtp=sent_via_smtp,
            owner_saved=owner_ok,
            user_saved=user_ok,
            smtp_queued=False,
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
