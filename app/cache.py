from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: datetime


@dataclass
class FeedCache:
    ttl_seconds: int = 15
    _entries: dict[str, CacheEntry] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= datetime.now(timezone.utc):
                self._entries.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._entries[key] = CacheEntry(
                value=value,
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds),
            )

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


feed_cache = FeedCache()
