"""Data models for CrossPoint API responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeviceStatus:
    """Response from GET /api/status."""

    version: str
    ip: str
    mode: str
    rssi: int
    free_heap: int
    uptime: int

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> DeviceStatus:
        return cls(
            version=data["version"],
            ip=data["ip"],
            mode=data["mode"],
            rssi=data["rssi"],
            free_heap=data["freeHeap"],
            uptime=data["uptime"],
        )


@dataclass(frozen=True)
class FileEntry:
    """Single item from GET /api/files."""

    name: str
    size: int
    is_directory: bool
    is_epub: bool

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> FileEntry:
        return cls(
            name=data["name"],
            size=data["size"],
            is_directory=data["isDirectory"],
            is_epub=data["isEpub"],
        )
