from __future__ import annotations

from django.conf import settings

from developer_landing.contact.repositories.contact_repository import ContactRepository
from developer_landing.contact.repositories.file_storage import JsonFileStore


class MetricsService:
    def __init__(self) -> None:
        self.store = JsonFileStore(settings.STORAGE_METRICS_FILE)
        self.contacts = ContactRepository()

    def increment(self, key: str = "total_contacts") -> None:
        data = self.store.read(
            default={
                "total_contacts": 0,
                "ai_success": 0,
                "ai_fallback": 0,
                "emails_sent": 0,
                "emails_file_fallback": 0,
            },
        )
        data[key] = int(data.get(key, 0)) + 1
        self.store.write(data)

    def snapshot(self) -> dict:
        file_metrics = self.store.read(
            default={
                "total_contacts": 0,
                "ai_success": 0,
                "ai_fallback": 0,
                "emails_sent": 0,
                "emails_file_fallback": 0,
            },
        )
        return {
            "file_metrics": file_metrics,
            "db_total": self.contacts.count(),
            "db_by_type": self.contacts.count_by_type(),
        }
