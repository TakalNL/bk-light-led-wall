"""Bounded connections; no handshake, pairing request, or application writes."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable

from bleak import BleakClient
from bleak.exc import BleakError

from .discovery import positive_seconds, resolve_device

logger = logging.getLogger(__name__)


@asynccontextmanager
async def connection(
    identifier: str,
    *,
    scan_timeout: float = 10.0,
    connect_timeout: float = 20.0,
    disconnected_callback: Callable | None = None,
    winrt_options: dict | None = None,
    service_uuids: list[str] | None = None,
    discovered_callback: Callable | None = None,
) -> AsyncIterator[tuple[Any, Any]]:
    positive_seconds(connect_timeout)
    device = await resolve_device(identifier, scan_timeout)
    if discovered_callback is not None:
        discovered_callback(device)
    options = {"disconnected_callback": disconnected_callback}
    if winrt_options is not None:
        options["winrt"] = winrt_options
    if service_uuids is not None:
        options["services"] = service_uuids
    client = BleakClient(device, **options)
    try:
        async with asyncio.timeout(connect_timeout):
            await client.connect()
        if not client.is_connected:
            raise ConnectionError("The Bluetooth connection did not stay open.")
        yield device, client
    finally:
        # Attempt cleanup even after a partially failed connection or cancellation.
        try:
            async with asyncio.timeout(5.0):
                await client.disconnect()
        except (BleakError, OSError, TimeoutError):
            logger.warning("Bluetooth disconnect cleanup failed; the OS may still be closing the link.")
