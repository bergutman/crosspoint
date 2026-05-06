"""Persistent upload queue for CrossPoint scripts.

When the device is offline, files can be queued and transferred later
via `python -m crosspoint queue --process`.
"""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import CrossPointClient


QUEUE_DIR = Path.home() / ".local" / "share" / "crosspoint" / "queue"
QUEUE_FILE = QUEUE_DIR / "queue.json"
MAX_RETRIES = 3


@dataclass
class QueueEntry:
    id: str
    filename: str
    source_path: str
    remote_dir: str
    host: str
    created_at: str
    attempts: int = 0


class UploadQueue:
    """Manages a persistent queue of files waiting to upload to the CrossPoint."""

    def __init__(self, queue_dir: Path | None = None) -> None:
        self.queue_dir = queue_dir or QUEUE_DIR
        self.queue_file = self.queue_dir / "queue.json"
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict[str, Any]]:
        if not self.queue_file.exists():
            return []
        with self.queue_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, entries: list[dict[str, Any]]) -> None:
        with self.queue_file.open("w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)

    def add(
        self,
        source_path: Path | str,
        remote_dir: str = "/",
        host: str = "crosspoint.local",
    ) -> QueueEntry:
        """Copy a file into the queue and record it for later upload."""
        source_path = Path(source_path).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Cannot queue missing file: {source_path}")

        entry_id = uuid.uuid4().hex[:12]
        stored_path = self.queue_dir / f"{entry_id}_{source_path.name}"
        shutil.copy2(source_path, stored_path)

        entry = QueueEntry(
            id=entry_id,
            filename=source_path.name,
            source_path=str(stored_path),
            remote_dir=remote_dir,
            host=host,
            created_at=datetime.now(timezone.utc).isoformat(),
            attempts=0,
        )

        entries = self._load()
        entries.append(asdict(entry))
        self._save(entries)
        return entry

    def list(self) -> list[QueueEntry]:
        """Return all queued entries."""
        raw = self._load()
        return [QueueEntry(**item) for item in raw]

    def clear(self) -> int:
        """Remove all queued entries and their stored files."""
        entries = self._load()
        count = len(entries)
        for item in entries:
            path = Path(item["source_path"])
            if path.exists():
                path.unlink()
        self._save([])
        return count

    def process(
        self,
        host: str | None = None,
        client: CrossPointClient | None = None,
    ) -> tuple[int, int]:
        """Attempt to upload all queued files.

        Returns (success_count, failure_count).
        """
        entries = self._load()
        if not entries:
            return 0, 0

        remaining: list[dict[str, Any]] = []
        successes = 0
        failures = 0

        for item in entries:
            entry = QueueEntry(**item)

            # Skip exhausted retries
            if entry.attempts >= MAX_RETRIES:
                print(f"Skipping {entry.filename} (exhausted {MAX_RETRIES} attempts)")
                remaining.append(asdict(entry))
                failures += 1
                continue

            # Use provided client or create one from entry host
            upload_client = client
            if upload_client is None:
                upload_client = CrossPointClient(host=host or entry.host)

            try:
                upload_client.upload_file(entry.source_path, entry.remote_dir, filename=entry.filename)
                print(f"Uploaded: {entry.filename} → {entry.remote_dir}")
                Path(entry.source_path).unlink(missing_ok=True)
                successes += 1
            except Exception as exc:
                entry.attempts += 1
                print(f"Failed ({entry.attempts}/{MAX_RETRIES}): {entry.filename} — {exc}")
                remaining.append(asdict(entry))
                failures += 1

        self._save(remaining)
        return successes, failures
