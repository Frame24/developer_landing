from __future__ import annotations

import logging
import time

logger = logging.getLogger("developer_landing.contact.requests")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - started) * 1000
        client_ip = self._client_ip(request)
        logger.info(
            "%s %s status=%s ip=%s duration_ms=%.1f",
            request.method,
            request.get_full_path(),
            getattr(response, "status_code", "-"),
            client_ip,
            duration_ms,
        )
        return response

    def _client_ip(self, request) -> str:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
