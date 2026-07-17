from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from django.db import close_old_connections

from developer_landing.contact.models import ContactRequest
from developer_landing.contact.repositories.contact_repository import ContactRepository
from developer_landing.contact.services.ai_service import AIService
from developer_landing.contact.services.email_service import EmailService
from developer_landing.contact.services.metrics_service import MetricsService

logger = logging.getLogger("developer_landing.contact")


class ContactDeliveryError(Exception):
    """Raised when contact emails cannot be delivered via SMTP or file fallback."""


@dataclass
class ContactProcessResult:
    contact: ContactRequest
    ai_available: bool
    request_type: str | None
    ai_reply: str | None
    email_via_smtp: bool
    email_queued: bool = False
    email_delivery_to: str | None = None


class ContactService:
    def __init__(self) -> None:
        self.repository = ContactRepository()
        self.ai_service = AIService()
        self.email_service = EmailService()
        self.metrics_service = MetricsService()

    def process(
        self,
        *,
        name: str,
        phone: str,
        email: str,
        comment: str,
        client_ip: str | None,
    ) -> ContactProcessResult:
        contact = self.repository.create(
            name=name,
            phone=phone,
            email=email,
            comment=comment,
            request_type="",
            ai_reply="",
            ai_available=False,
            client_ip=client_ip,
        )
        self.metrics_service.increment("total_contacts")

        delivery_to = self.email_service.effective_delivery_address(email)
        thread = threading.Thread(
            target=self._process_ai_and_email,
            kwargs={
                "contact_id": contact.id,
                "name": name,
                "phone": phone,
                "email": email,
                "comment": comment,
            },
            daemon=True,
            name=f"contact-ai-email-{contact.id}",
        )
        thread.start()
        logger.info("AI+email queued in background for contact #%s", contact.id)

        return ContactProcessResult(
            contact=contact,
            ai_available=False,
            request_type=None,
            ai_reply=None,
            email_via_smtp=False,
            email_queued=True,
            email_delivery_to=delivery_to,
        )

    def _process_ai_and_email(
        self,
        *,
        contact_id: int,
        name: str,
        phone: str,
        email: str,
        comment: str,
    ) -> None:
        close_old_connections()
        request_type = None
        ai_reply = None
        ai_available = False
        try:
            try:
                ai_result = self.ai_service.analyze(name=name, comment=comment)
                request_type = ai_result.request_type
                ai_reply = ai_result.reply
                ai_available = ai_result.available
                if ai_result.available:
                    self.metrics_service.increment("ai_success")
                else:
                    self.metrics_service.increment("ai_fallback")
                self.repository.update_ai_fields(
                    contact_id,
                    request_type=ai_result.request_type or "",
                    ai_reply=ai_result.reply or "",
                    ai_available=ai_result.available,
                )
            except Exception:
                logger.exception(
                    "Background AI failed for contact #%s; sending email anyway",
                    contact_id,
                )
                self.metrics_service.increment("ai_fallback")

            email_result = self.email_service.send_contact_notifications(
                name=name,
                phone=phone,
                email=email,
                comment=comment,
                request_type=request_type,
                ai_reply=ai_reply,
                ai_available=ai_available,
            )
            if email_result.sent_via_smtp:
                self.metrics_service.increment("emails_sent")
            else:
                self.metrics_service.increment("emails_file_fallback")

            if not (email_result.owner_saved and email_result.user_saved):
                logger.error(
                    "Failed to save contact email copies to file storage "
                    "(contact #%s)",
                    contact_id,
                )
            logger.info(
                "Background AI+email done for contact #%s (type=%s smtp=%s to=%s)",
                contact_id,
                request_type,
                email_result.sent_via_smtp,
                email_result.delivery_to,
            )
        except Exception:
            logger.exception("Background AI+email failed for contact #%s", contact_id)
        finally:
            close_old_connections()
