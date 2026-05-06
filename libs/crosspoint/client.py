"""HTTP and WebSocket client for the CrossPoint Reader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
import websocket

from .models import DeviceStatus, FileEntry


class CrossPointError(Exception):
    """Base exception for CrossPoint client errors."""


class CrossPointClient:
    """Client for the CrossPoint Reader web API."""

    def __init__(self, host: str = "crosspoint.local", http_port: int = 80, ws_port: int = 81) -> None:
        self.host = host
        self.http_port = http_port
        self.ws_port = ws_port
        self._session = requests.Session()

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.http_port}"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self.ws_port}/"

    def _get(self, path: str, params: dict[str, Any] | None = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        response = self._session.get(url, params=params or {}, timeout=30)
        response.raise_for_status()
        return response

    def _post(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        response = self._session.post(url, params=params or {}, data=data or {}, files=files, timeout=120)
        response.raise_for_status()
        return response

    def status(self) -> DeviceStatus:
        """Fetch device status from /api/status."""
        resp = self._get("/api/status")
        return DeviceStatus.from_json(resp.json())

    def list_files(self, path: str = "/") -> list[FileEntry]:
        """List files and folders from /api/files."""
        resp = self._get("/api/files", params={"path": path})
        return [FileEntry.from_json(item) for item in resp.json()]

    def upload_file(self, local_path: Path | str, remote_dir: str = "/", filename: str | None = None) -> str:
        """Upload a file via HTTP multipart POST /upload."""
        local_path = Path(local_path)
        if not local_path.exists():
            raise CrossPointError(f"Local file not found: {local_path}")

        upload_name = filename or local_path.name
        with local_path.open("rb") as f:
            files = {"file": (upload_name, f)}
            resp = self._post("/upload", params={"path": remote_dir}, files=files)
        return resp.text

    def mkdir(self, name: str, parent: str = "/") -> str:
        """Create a folder via POST /mkdir."""
        resp = self._post("/mkdir", data={"name": name, "path": parent})
        return resp.text

    def delete(self, path: str, item_type: str = "file") -> str:
        """Delete a file or folder via POST /delete."""
        resp = self._post("/delete", data={"path": path, "type": item_type})
        return resp.text

    def upload_file_ws(
        self,
        local_path: Path | str,
        remote_dir: str = "/",
        chunk_size: int = 65536,
    ) -> None:
        """Upload a file via the WebSocket fast binary protocol on port 81."""
        local_path = Path(local_path)
        if not local_path.exists():
            raise CrossPointError(f"Local file not found: {local_path}")

        file_size = local_path.stat().st_size
        start_msg = f"START:{local_path.name}:{file_size}:{remote_dir}"

        ws = websocket.create_connection(self.ws_url)
        try:
            ws.send(start_msg)
            response = ws.recv()
            if response != "READY":
                raise CrossPointError(f"WebSocket upload not ready: {response}")

            with local_path.open("rb") as f:
                while chunk := f.read(chunk_size):
                    ws.send_binary(chunk)

            # Wait for final DONE or ERROR
            while True:
                response = ws.recv()
                if isinstance(response, str):
                    if response == "DONE":
                        return
                    if response.startswith("ERROR:"):
                        raise CrossPointError(f"WebSocket upload failed: {response}")
        finally:
            ws.close()
