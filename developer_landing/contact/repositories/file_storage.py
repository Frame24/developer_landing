from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


_lock = threading.Lock()


class JsonFileStore:
    """Thread-safe JSON file helper for rate limit and metrics."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self, default: Any) -> Any:
        with _lock:
            if not self.path.exists():
                return default
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return default

    def write(self, data: Any) -> None:
        with _lock:
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
