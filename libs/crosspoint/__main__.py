"""CLI entry point for quick device checks."""

from __future__ import annotations

import argparse
import sys

from .client import CrossPointClient


def main() -> int:
    parser = argparse.ArgumentParser(description="CrossPoint Reader CLI")
    parser.add_argument("--host", default="crosspoint.local", help="Device hostname or IP")
    parser.add_argument("--port", type=int, default=80, help="HTTP port")
    subparsers = parser.add_subparsers(dest="command")

    status_parser = subparsers.add_parser("status", help="Get device status")
    ls_parser = subparsers.add_parser("ls", help="List files on device")
    ls_parser.add_argument("--path", default="/", help="Directory path to list")
    upload_parser = subparsers.add_parser("upload", help="Upload a file")
    upload_parser.add_argument("file", help="Local file path")
    upload_parser.add_argument("--dir", default="/", help="Remote directory")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    client = CrossPointClient(host=args.host, http_port=args.port)

    if args.command == "status":
        status = client.status()
        print(f"Version:  {status.version}")
        print(f"IP:       {status.ip}")
        print(f"Mode:     {status.mode}")
        print(f"RSSI:     {status.rssi} dBm")
        print(f"Free heap: {status.free_heap} bytes")
        print(f"Uptime:   {status.uptime} seconds")

    elif args.command == "ls":
        entries = client.list_files(args.path)
        for entry in entries:
            kind = "DIR " if entry.is_directory else "FILE"
            print(f"{kind:4} {entry.size:>10}  {entry.name}")

    elif args.command == "upload":
        result = client.upload_file(args.file, args.dir)
        print(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
