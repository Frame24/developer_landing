from __future__ import annotations

import logging
import traceback

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("developer_landing.contact")


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is not None:
        if isinstance(response.data, dict):
            payload = {
                "success": False,
                "error": {
                    "status_code": response.status_code,
                    "details": response.data,
                },
            }
            response.data = payload
        return response

    logger.error(
        "Unhandled exception in %s: %s\n%s",
        context.get("view"),
        exc,
        traceback.format_exc(),
    )
    return Response(
        {
            "success": False,
            "error": {
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": "Внутренняя ошибка сервера.",
            },
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
