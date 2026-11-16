"""Query published iPixel device info (also syncs the panel's clock) and versions."""

import argparse
import asyncio
from pathlib import Path
from zoneinfo import ZoneInfo

from led_matrix_hacker.experiments import Recorder
from led_matrix_hacker.library_link import library_connection


async def experiment(device, output, timezone_name):
    ZoneInfo(timezone_name)
    record = Recorder(output)
    record("experiment", name="reference-device-information", timezone=timezone_name,
           clock_side_effect="synchronize panel time-of-day using the selected timezone")
    try:
        async with library_connection(device, record, windows_cached_services=False, write_delay=.01) as link:
            await link.initialize(timezone_name=timezone_name, required_dimensions=None)
        record("finished")
    except BaseException as error:
        record("error", error_type=type(error).__name__, message=str(error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device")
    parser.add_argument("--timezone", default="Europe/Berlin", help="IANA timezone for panel clock sync")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ZoneInfo(args.timezone)  # Fail before Bluetooth or capture creation if unavailable.
    with args.output.open("x", encoding="utf-8") as output:
        asyncio.run(experiment(args.device, output, args.timezone))


if __name__ == "__main__":
    main()
