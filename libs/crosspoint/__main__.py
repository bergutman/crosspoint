"""CLI entry point for quick device checks."""

from __future__ import annotations

import argparse
import sys

from .client import CrossPointClient
from .queue import UploadQueue


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

    queue_parser = subparsers.add_parser("queue", help="Manage upload queue")
    queue_parser.add_argument("--process", action="store_true", help="Process all queued uploads")
    queue_parser.add_argument("--clear", action="store_true", help="Clear the queue")

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

    elif args.command == "queue":
        queue = UploadQueue()

        if args.clear:
            count = queue.clear()
            print(f"Cleared {count} item(s) from queue.")
            return 0

        if args.process:
            successes, failures = queue.process(client=client)
            print(f"\nDone: {successes} uploaded, {failures} failed/remaining.")
            return 0

        entries = queue.list()
        if not entries:
            print("Queue is empty.")
            return 0

        print(f"{'ID':<14} {'Filename':<30} {'Directory':<15} {'Host':<20} {'Attempts'}")
        print("-" * 90)
        for e in entries:
            print(f"{e.id:<14} {e.filename:<30} {e.remote_dir:<15} {e.host:<20} {e.attempts}/{3}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
