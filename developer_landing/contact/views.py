from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from developer_landing.contact.serializers import ContactSerializer
from developer_landing.contact.services.ai_service import AIService
from developer_landing.contact.services.contact_service import ContactService
from developer_landing.contact.services.metrics_service import MetricsService
from developer_landing.contact.services.rate_limit_service import RateLimitService


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
        description="Принять обращение с формы, прогнать через AI и отправить email.",
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
        return Response(
            {
                "success": True,
                "data": {
                    "status": "ok",
                    "ai_configured": ai.is_configured(),
                    "smtp_configured": bool(settings.EMAIL_HOST),
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
