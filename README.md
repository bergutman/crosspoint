# CrossPoint Scripts

A monorepo of automation scripts for the [CrossPoint Reader](https://github.com/crosspoint-reader/crosspoint-reader) custom firmware on the xTeInk X4 e-ink reader.

## Quick Start

```bash
# Create a virtual environment
python -m venv .venv

# If you use direnv, run `direnv allow` now — the .envrc will activate it automatically.
# Otherwise activate manually:
source .venv/bin/activate

# Install the shared library and dependencies
pip install -e ".[dev,epub]"

# Test connectivity to your device
python -m crosspoint --host 192.168.68.51 status

# Manage upload queue
python -m crosspoint queue               # list pending uploads
python -m crosspoint queue --process     # upload everything queued
```

## Monorepo Layout

```
.
├── libs/
│   └── crosspoint/          # Shared Python client for the CrossPoint HTTP + WebSocket API
├── projects/                # Individual automation projects (one per folder)
│   └── (your projects here)
├── docs/
│   └── api.md               # Cached copy of the webserver endpoint documentation
└── pyproject.toml           # Workspace-level configuration
```

## API Reference

The CrossPoint exposes an HTTP server on port 80 and a WebSocket on port 81. See [`docs/api.md`](docs/api.md) for the full endpoint documentation.

Key endpoints:
- `GET /api/status` — Device status (version, IP, RSSI, uptime, free heap)
- `GET /api/files?path=/` — List files and folders on the SD card
- `POST /upload` — Upload a file via multipart form
- `POST /mkdir` — Create a folder
- `POST /delete` — Delete a file or folder
- `WebSocket :81` — Fast binary upload protocol

## Adding a New Project

1. Create a new folder under `projects/`
2. Add a `README.md` describing what it does
3. Add a `pyproject.toml` or `requirements.txt` if it needs extra deps beyond the workspace
4. Import from `crosspoint` to talk to the device:

```python
from crosspoint import CrossPointClient

client = CrossPointClient("192.168.68.51")
client.upload_file("mybook.epub", "/Books")
```

## Device IP

If your network does not support mDNS (`crosspoint.local`), use the IP shown on the device screen. The current home IP is **192.168.68.51**.
