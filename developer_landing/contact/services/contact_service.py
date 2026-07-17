from __future__ import annotations

import logging
from dataclasses import dataclass

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
        ai_result = self.ai_service.analyze(name=name, comment=comment)
        if ai_result.available:
            self.metrics_service.increment("ai_success")
        else:
            self.metrics_service.increment("ai_fallback")

        contact = self.repository.create(
            name=name,
            phone=phone,
            email=email,
            comment=comment,
            request_type=ai_result.request_type or "",
            ai_reply=ai_result.reply or "",
            ai_available=ai_result.available,
            client_ip=client_ip,
        )
        self.metrics_service.increment("total_contacts")

        email_result = self.email_service.send_contact_notifications(
            name=name,
            phone=phone,
            email=email,
            comment=comment,
            request_type=ai_result.request_type,
            ai_reply=ai_result.reply,
            ai_available=ai_result.available,
        )
        if email_result.sent_via_smtp:
            self.metrics_service.increment("emails_sent")
        else:
            self.metrics_service.increment("emails_file_fallback")

        if not (email_result.owner_saved and email_result.user_saved):
            # Contact is already stored in DB; do not fail the whole request.
            logger.error("Failed to save contact email copies to file storage")

        return ContactProcessResult(
            contact=contact,
            ai_available=ai_result.available,
            request_type=ai_result.request_type,
            ai_reply=ai_result.reply,
            email_via_smtp=email_result.sent_via_smtp,
        )
