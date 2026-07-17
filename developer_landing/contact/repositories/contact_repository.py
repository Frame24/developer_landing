from __future__ import annotations

from developer_landing.contact.models import ContactRequest


class ContactRepository:
    def create(
        self,
        *,
        name: str,
        phone: str,
        email: str,
        comment: str,
        request_type: str = "",
        ai_reply: str = "",
        ai_available: bool = False,
        client_ip: str | None = None,
    ) -> ContactRequest:
        return ContactRequest.objects.create(
            name=name,
            phone=phone,
            email=email,
            comment=comment,
            request_type=request_type,
            ai_reply=ai_reply,
            ai_available=ai_available,
            client_ip=client_ip,
        )

    def update_ai_fields(
        self,
        contact_id: int,
        *,
        request_type: str,
        ai_reply: str,
        ai_available: bool,
    ) -> None:
        ContactRequest.objects.filter(pk=contact_id).update(
            request_type=request_type,
            ai_reply=ai_reply,
            ai_available=ai_available,
        )

    def count(self) -> int:
        return ContactRequest.objects.count()

    def count_by_type(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for value, _label in ContactRequest.RequestType.choices:
            result[value] = ContactRequest.objects.filter(request_type=value).count()
        result["unclassified"] = ContactRequest.objects.filter(request_type="").count()
        return result
