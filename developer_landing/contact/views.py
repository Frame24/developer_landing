from __future__ import annotations

import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from developer_landing.contact.serializers import ContactSerializer
from developer_landing.contact.services.ai_service import AIService
from developer_landing.contact.services.contact_service import ContactService
from developer_landing.contact.services.email_service import EmailService
from developer_landing.contact.services.mail_inbox_service import MailInboxService
from developer_landing.contact.services.metrics_service import MetricsService
from developer_landing.contact.services.rate_limit_service import RateLimitService

logger = logging.getLogger("developer_landing.contact")


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


class ContactCreateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=ContactSerializer,
        responses={201: dict, 400: dict, 429: dict, 500: dict},
        description=(
            "Принять обращение с формы. AI и email запускаются в фоне "
            "сразу после сохранения заявки."
        ),
    )
    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        client_ip = _client_ip(request)
        rate = RateLimitService().check(client_ip)
        if not rate.allowed:
            return Response(
                {
                    "success": False,
                    "error": {
                        "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                        "details": "Слишком много запросов. Попробуйте позже.",
                        "retry_after": rate.retry_after,
                    },
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(rate.retry_after)},
            )

        try:
            result = ContactService().process(
                name=serializer.validated_data["name"],
                phone=serializer.validated_data["phone"],
                email=serializer.validated_data["email"],
                comment=serializer.validated_data["comment"],
                client_ip=client_ip,
            )
        except Exception:
            logger.exception("Contact processing failed")
            return Response(
                {
                    "success": False,
                    "error": {
                        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "details": "Не удалось обработать обращение.",
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "data": {
                    "id": result.contact.id,
                    "ai_available": result.ai_available,
                    "request_type": result.request_type,
                    "ai_reply": result.ai_reply,
                    "email_via_smtp": result.email_via_smtp,
                    "email_queued": result.email_queued,
                    "email_delivery_to": result.email_delivery_to,
                    "rate_limit_remaining": rate.remaining,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: dict})
    def get(self, request):
        ai = AIService()
        inbox = MailInboxService().list_recent(limit=5)
        return Response(
            {
                "success": True,
                "data": {
                    "status": "ok",
                    "ai_configured": ai.is_configured(),
                    "smtp_configured": EmailService().is_configured(),
                    "email_demo_force_to": settings.EMAIL_DEMO_FORCE_TO or None,
                    "mail_stored_recent": inbox["count"],
                    "debug": settings.DEBUG,
                },
            },
        )


class MetricsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: dict})
    def get(self, request):
        return Response(
            {
                "success": True,
                "data": MetricsService().snapshot(),
            },
        )


class MailInboxView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        responses={200: dict},
        description="Демо-лента сохранённых писем (owner + AI reply copies).",
    )
    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 20))
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(limit, 50))
        return Response(
            {
                "success": True,
                "data": MailInboxService().list_recent(limit=limit),
            },
        )
