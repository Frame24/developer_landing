from __future__ import annotations

from datetime import datetime
from pathlib import Path

from django.conf import settings


class MailInboxService:
    """Read stored mail copies from storage/mail for demo /api/mail."""

    def list_recent(self, *, limit: int = 20) -> dict:
        directory: Path = settings.STORAGE_MAIL_DIR
        directory.mkdir(parents=True, exist_ok=True)
        files = sorted(
            directory.glob("*.txt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]

        items = []
        for path in files:
            text = path.read_text(encoding="utf-8", errors="replace")
            meta, body = self._split_meta(text)
            kind = meta.get("kind") or self._kind_from_name(path.name)
            preview = " ".join(body.split())[:180]
            items.append(
                {
                    "filename": path.name,
                    "kind": kind,
                    "subject": meta.get("subject", ""),
                    "original_email": meta.get("original_email", ""),
                    "delivery_to": meta.get("delivery_to", ""),
                    "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(
                        timespec="seconds",
                    ),
                    "preview": preview,
                    "body": body.strip(),
                },
            )

        return {
            "count": len(items),
            "demo_force_to": settings.EMAIL_DEMO_FORCE_TO or None,
            "storage_dir": str(directory),
            "items": items,
        }

    @staticmethod
    def _kind_from_name(filename: str) -> str:
        if filename.startswith("owner_"):
            return "owner"
        if filename.startswith("user_"):
            return "user_reply"
        return "unknown"

    @staticmethod
    def _split_meta(text: str) -> tuple[dict[str, str], str]:
        if "\n---\n" not in text:
            return {}, text
        header, body = text.split("\n---\n", 1)
        meta: dict[str, str] = {}
        for line in header.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
        # Old files without meta headers shouldn't lose content.
        if not meta:
            return {}, text
        return meta, body
