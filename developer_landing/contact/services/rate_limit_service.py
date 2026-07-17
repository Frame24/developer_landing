from __future__ import annotations

import time
from dataclasses import dataclass

from django.conf import settings

from developer_landing.contact.repositories.file_storage import JsonFileStore


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int


class RateLimitService:
    def __init__(self) -> None:
        self.store = JsonFileStore(settings.STORAGE_RATE_LIMIT_DIR / "rate_limit.json")
        self.max_requests = settings.RATE_LIMIT_MAX
        self.window = settings.RATE_LIMIT_WINDOW_SECONDS

    def check(self, client_ip: str) -> RateLimitResult:
        now = time.time()
        data = self.store.read(default={})
        timestamps = [float(ts) for ts in data.get(client_ip, []) if now - float(ts) < self.window]
        if len(timestamps) >= self.max_requests:
            oldest = min(timestamps) if timestamps else now
            retry_after = max(1, int(self.window - (now - oldest)))
            data[client_ip] = timestamps
            self.store.write(data)
            return RateLimitResult(allowed=False, remaining=0, retry_after=retry_after)

        timestamps.append(now)
        data[client_ip] = timestamps
        # prune stale keys occasionally
        cleaned = {
            ip: [ts for ts in stamps if now - float(ts) < self.window]
            for ip, stamps in data.items()
        }
        cleaned = {ip: stamps for ip, stamps in cleaned.items() if stamps}
        cleaned[client_ip] = timestamps
        self.store.write(cleaned)
        remaining = max(0, self.max_requests - len(timestamps))
        return RateLimitResult(allowed=True, remaining=remaining, retry_after=0)
