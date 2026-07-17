from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
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
    delivery_to: str | None = None


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
        delivery_to = self.effective_delivery_address(email)
        owner_body = self._owner_body(
            name=name,
            phone=phone,
            email=email,
            comment=comment,
            request_type=request_type,
            ai_available=ai_available,
            delivery_to=delivery_to,
        )
        user_body = self._user_body(
            name=name,
            comment=comment,
            ai_reply=ai_reply,
            ai_available=ai_available,
            original_email=email,
            delivery_to=delivery_to,
        )

        owner_ok = self._save_to_file(
            "owner",
            owner_body,
            meta={
                "kind": "owner",
                "original_email": email,
                "delivery_to": delivery_to,
                "subject": f"[Contact] Новое обращение от {name}",
            },
        )
        user_ok = self._save_to_file(
            "user",
            user_body,
            meta={
                "kind": "user_reply",
                "original_email": email,
                "delivery_to": delivery_to,
                "subject": "Мы получили ваше обращение",
            },
        )

        # Delivery runs inline. Caller already schedules this in a background thread.
        sent_via_smtp = False
        if self.is_configured():
            try:
                self._send_pair(
                    owner_subject=f"[Contact] Новое обращение от {name}",
                    owner_body=owner_body,
                    user_subject="Мы получили ваше обращение",
                    user_body=user_body,
                    delivery_to=delivery_to,
                )
                sent_via_smtp = True
                logger.info(
                    "Email sent to %s (original form email=%s via=%s)",
                    delivery_to,
                    email,
                    "resend_api" if self._uses_resend() else "smtp",
                )
            except Exception:
                logger.exception(
                    "Email send failed (to=%s original=%s)",
                    delivery_to,
                    email,
                )

        return EmailResult(
            sent_via_smtp=sent_via_smtp,
            owner_saved=owner_ok,
            user_saved=user_ok,
            smtp_queued=False,
            delivery_to=delivery_to,
        )

    @staticmethod
    def effective_delivery_address(original_email: str) -> str:
        forced = (settings.EMAIL_DEMO_FORCE_TO or "").strip()
        if forced:
            return forced
        return settings.CONTACT_OWNER_EMAIL or original_email

    def is_configured(self) -> bool:
        return bool(
            settings.EMAIL_HOST
            and settings.EMAIL_HOST_USER
            and settings.EMAIL_HOST_PASSWORD
            and (settings.EMAIL_DEMO_FORCE_TO or settings.CONTACT_OWNER_EMAIL)
        )

    def _smtp_configured(self) -> bool:
        return self.is_configured()

    @staticmethod
    def _uses_resend() -> bool:
        host = (settings.EMAIL_HOST or "").lower()
        return "resend" in host

    def _send_pair(
        self,
        *,
        owner_subject: str,
        owner_body: str,
        user_subject: str,
        user_body: str,
        delivery_to: str,
    ) -> None:
        # Resend SMTP (port 587) often times out behind VPN; HTTPS API is reliable.
        send = self._send_resend_api if self._uses_resend() else self._send_smtp
        send(subject=owner_subject, body=owner_body, to=[delivery_to])
        send(subject=user_subject, body=user_body, to=[delivery_to])

    def _send_resend_api(self, *, subject: str, body: str, to: list[str]) -> None:
        payload = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": to,
            "subject": subject,
            "text": body,
        }
        request = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {settings.EMAIL_HOST_PASSWORD}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                # Cloudflare blocks default urllib User-Agent (error 1010).
                "User-Agent": (
                    "developer-landing/1.0 "
                    "(+https://github.com/Frame24/developer_landing)"
                ),
            },
        )
        timeout = int(getattr(settings, "EMAIL_TIMEOUT", 20) or 20)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                logger.info("Resend API OK status=%s body=%s", response.status, raw[:200])
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.error("Resend API HTTP %s: %s", exc.code, detail)
            raise

    def _send_smtp(self, *, subject: str, body: str, to: list[str]) -> None:
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
        )
        message.send(fail_silently=False)

    def _save_to_file(self, prefix: str, body: str, *, meta: dict | None = None) -> bool:
        try:
            directory: Path = settings.STORAGE_MAIL_DIR
            directory.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = directory / f"{prefix}_{stamp}.txt"
            header_lines = []
            if meta:
                for key, value in meta.items():
                    header_lines.append(f"{key}: {value}")
                header_lines.append("---")
            content = "\n".join(header_lines + [body]) if header_lines else body
            path.write_text(content, encoding="utf-8")
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
        delivery_to: str,
    ) -> str:
        demo_note = ""
        if settings.EMAIL_DEMO_FORCE_TO:
            demo_note = (
                f"[DEMO] Доставка принудительно на {delivery_to} "
                f"(Resend test mode без своего домена).\n"
                f"Email из формы: {email}\n\n"
            )
        return (
            f"{demo_note}"
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
        original_email: str,
        delivery_to: str,
    ) -> str:
        reply = ai_reply if ai_available and ai_reply else (
            "Спасибо за обращение! Мы получили ваше сообщение и ответим в ближайшее время."
        )
        demo_note = ""
        if settings.EMAIL_DEMO_FORCE_TO:
            demo_note = (
                f"[DEMO] Это копия ответа пользователю. "
                f"В тестовом режиме Resend письмо уходит на {delivery_to}, "
                f"а не на {original_email}.\n\n"
            )
        return (
            f"{demo_note}"
            f"Здравствуйте, {name}!\n\n"
            f"{reply}\n\n"
            "---\n"
            "Ваше сообщение:\n"
            f"{comment}\n"
        )
