"""Read-only discovery CLI with opt-in JSON and notification recording."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from contextlib import nullcontext
from pathlib import Path
from uuid import UUID

from bleak.exc import BleakError

from .discovery import positive_seconds, scan
from .inspection import inspect_device, listen


def seconds(value: str) -> float:
    try:
        return positive_seconds(float(value))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use a finite number of seconds greater than zero.") from error


def positive_integer(value: str) -> int:
    try:
        result = int(value)
        if result <= 0:
            raise ValueError
        return result
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use a positive integer.") from error


def characteristic(value: str) -> str | int:
    try:
        if value.startswith("0x") or value.isdecimal():
            handle = int(value, 16 if value.startswith("0x") else 10)
            if not 0 < handle <= 0xFFFF:
                raise ValueError
            return handle
        return str(UUID(value))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use a full characteristic UUID or handle (decimal or 0xHEX).") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Investigate BLE metadata without sending display commands.")
    parser.add_argument("--verbose", action="store_true", help="Enable project debug logging.")
    commands = parser.add_subparsers(dest="command", required=True)
    scanner = commands.add_parser("scan", help="Scan BLE advertisements without connecting.")
    scanner.add_argument("--timeout", type=seconds, default=10.0)
    scanner.add_argument("--name", help="Case-insensitive name substring; no filter by default.")
    scanner.add_argument("--include-payloads", action="store_true", help="Include raw manufacturer/service data in JSON.")
    inspector = commands.add_parser("inspect", help="Connect and enumerate GATT metadata; no value reads or writes.")
    listener = commands.add_parser("listen", help="Explicitly subscribe to one characteristic (OS may write CCCD).")
    for command in (inspector, listener):
        command.add_argument("device", help="Current platform identifier or exact, unique advertised name.")
        command.add_argument("--scan-timeout", type=seconds, default=10.0)
        command.add_argument("--connect-timeout", type=seconds, default=20.0)
    for command in (scanner, inspector):
        command.add_argument("--json", action="store_true", help="Print JSON instead of the readable summary.")
        command.add_argument("--output", type=Path, help="Save JSON to a new file; existing files are preserved.")
    listener.add_argument("--characteristic", type=characteristic, required=True)
    listener.add_argument("--duration", type=seconds, default=30.0)
    listener.add_argument("--max-events", type=positive_integer, default=1000)
    listener.add_argument("--output", type=Path, help="Stream JSONL to a new file as well as stdout.")
    return parser


def print_report(report: dict, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    elif report["kind"] == "scan":
        for device in report["devices"]:
            name = device["advertised_name"] or device["name"] or "<unnamed>"
            rssi = device["rssi_dbm"]
            print(f"{device['identifier']}  {name!r}  RSSI: {rssi if rssi is not None else 'unavailable'}")
            print("  Advertised services: " + (", ".join(device["service_uuids"]) or "<none advertised>"))
        if not report["devices"]:
            print("No matching BLE advertisements. Check power, adapter, phone-app connection, and scan duration.")
            print("Bluetooth Classic-only devices do not appear in this scan.")
    else:
        print(f"Device: {report['device']['identifier']}  {report['device']['name']!r}")
        for service in report["services"]:
            print(f"Service {service['uuid']} (handle {service['handle']}) {service['description']}")
            for char in service["characteristics"]:
                print(f"  {char['uuid']} (handle {char['handle']}) [{', '.join(char['properties'])}]")
                print(f"    writable={char['writable']}  notifiable={char['notifiable']}")


async def run(args: argparse.Namespace) -> None:
    # Open exclusively before touching Bluetooth, so a bad output path fails early.
    output_context = args.output.open("x", encoding="utf-8") if args.output else nullcontext(None)
    with output_context as output:
        if args.command == "listen":
            print("Subscribing to the selected characteristic; the OS may write its CCCD. No display command is sent.", file=sys.stderr)

            def emit(record):
                line = json.dumps(record, ensure_ascii=True)
                if output:
                    output.write(line + "\n")
                    output.flush()
                print(line, flush=True)

            count = await listen(
                args.device, args.characteristic, emit,
                duration=args.duration, max_events=args.max_events,
                scan_timeout=args.scan_timeout, connect_timeout=args.connect_timeout,
            )
            print(f"Captured {count} notification(s).", file=sys.stderr)
            return
        if args.command == "scan":
            report = await scan(args.timeout, name_filter=args.name, include_payloads=args.include_payloads)
        else:
            report = await inspect_device(
                args.device, scan_timeout=args.scan_timeout, connect_timeout=args.connect_timeout
            )
        if output:
            json.dump(report, output, indent=2, ensure_ascii=True)
            output.write("\n")
        print_report(report, as_json=args.json)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    logging.getLogger("led_matrix_hacker").setLevel(logging.DEBUG if args.verbose else logging.WARNING)
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("Interrupted; captured JSONL events have already been flushed.", file=sys.stderr)
        return 130
    except (BleakError, OSError, ValueError, TimeoutError) as error:
        detail = str(error) or "Bluetooth operation timed out."
        print(f"Error: {detail}", file=sys.stderr)
        print("Check Bluetooth availability, OS permissions, device power, and disconnect the phone app.", file=sys.stderr)
        return 1
    return 0
