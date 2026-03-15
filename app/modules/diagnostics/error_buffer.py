"""
In-memory circular error buffer for the diagnostics panel.
Stores the last N application errors for operator visibility.
Thread-safe. Never persisted to disk or database.

v3.14: Operational Readiness
"""

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Optional

MAX_ENTRIES = 100


class ErrorBuffer:
    """Singleton circular buffer for application error events."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._buffer = deque(maxlen=MAX_ENTRIES)
                    cls._instance._buffer_lock = threading.Lock()
        return cls._instance

    def record(
        self,
        level: str,
        module: str,
        message: str,
        request_path: Optional[str] = None,
        exception_type: Optional[str] = None
    ) -> None:
        """
        Record an error event. Call this from exception handlers
        and error logging throughout the application.

        Args:
            level: "ERROR" | "WARNING" | "CRITICAL"
            module: Module or component name (e.g., "odicm", "auth", "ikf")
            message: Human-readable error description
            request_path: HTTP request path if applicable (e.g., "/api/v1/coaching")
            exception_type: Exception class name if applicable
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "module": module,
            "message": message[:500],       # Cap length
            "request_path": request_path,
            "exception_type": exception_type,
        }
        with self._buffer_lock:
            self._buffer.append(entry)

    def get_recent(self, limit: int = 50, level_filter: Optional[str] = None) -> list:
        """
        Return recent error events, newest first.
        Optionally filter by level ("ERROR", "WARNING", "CRITICAL").
        """
        with self._buffer_lock:
            entries = list(self._buffer)

        entries.reverse()  # Newest first

        if level_filter:
            entries = [e for e in entries if e["level"] == level_filter.upper()]

        return entries[:limit]

    def get_counts(self) -> dict:
        """Return error counts by level for the current buffer window."""
        with self._buffer_lock:
            entries = list(self._buffer)

        counts = {"ERROR": 0, "WARNING": 0, "CRITICAL": 0}
        for entry in entries:
            level = entry.get("level", "ERROR")
            counts[level] = counts.get(level, 0) + 1

        return counts

    def clear(self) -> None:
        """Clear all entries. Used in testing only."""
        with self._buffer_lock:
            self._buffer.clear()


# Module-level singleton
error_buffer = ErrorBuffer()
