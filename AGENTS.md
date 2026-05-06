# Agent Notes

## Project Context
- Monorepo for CrossPoint (xTeInk X4 e-reader) automation scripts.
- Shared library lives in `libs/crosspoint/`.
- Individual projects live in `projects/`.
- Device API docs are cached in `docs/api.md`.

## Code Style
- Python 3.10+
- Format with `ruff`.
- Type-check with `mypy --strict`.
- Prefer `pathlib.Path` over raw strings for filesystem paths.
- Prefer `httpx` over `requests` for new async code (but `requests` is fine for sync scripts).

## Device Defaults
- Default host: `crosspoint.local`
- Fallback IP (coffee shop): `172.20.10.8`
- HTTP API port: `80`
- WebSocket upload port: `81`
