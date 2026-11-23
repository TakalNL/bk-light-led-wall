"""One instrumented pypixelcolor backend for games and hardware experiments.

Upstream owns command framing, chunking and ACKs. This adapter supplies bounded
Windows connections, capture logging, strict reply checks and explicit timezones.
The public upstream Client connection lifecycle is not used.
"""

import asyncio
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
import sys
from zoneinfo import ZoneInfo

from pypixelcolor.lib.device_info import parse_device_info as upstream_device_info
from pypixelcolor.lib.internal_commands import build_get_hw_info_command
from pypixelcolor.lib.transport.ack_manager import AckManager
from pypixelcolor.lib.transport.send_plan import send_plan, single_window_plan

from .protocol import (
    SERVICE_UUID, WRITE_UUID, NOTIFY_UUID, device_info_request,
    parse_device_info, parse_versions,
)
from .transport import connection


class TracedClient:
    def __init__(self, client, record, *, write_delay=0):
        self.client, self.record, self.write_delay = client, record, write_delay
        self.notifications = deque(maxlen=512)
        self.write_count = 0
        self.notification_filter = None
        self.notification_error = None

    def __getattr__(self, name):
        return getattr(self.client, name)

    async def write_gatt_char(self, char, data, *, response):
        if self.notification_error is not None:
            raise self.notification_error
        self.write_count += 1
        self.record('library_write_attempt', number=self.write_count, response=response,
                    length=len(data), payload_hex=bytes(data).hex())
        async with asyncio.timeout(5):
            await self.client.write_gatt_char(char, data, response=response)
        if self.notification_error is not None:
            raise self.notification_error
        self.record('library_write_completed', number=self.write_count)
        if self.write_delay:
            await asyncio.sleep(self.write_delay)

    async def start_notify(self, char, callback):
        def observed(sender, data):
            payload = bytes(data)
            try:
                self.record('library_notification', payload_hex=payload.hex(), length=len(payload))
                if self.notification_filter is None or self.notification_filter(payload):
                    self.notifications.append(payload)
                    callback(sender, data)
            except Exception as error:
                self.notification_error = error
        async with asyncio.timeout(10):
            await self.client.start_notify(char, observed)

    async def stop_notify(self, char):
        async with asyncio.timeout(5):
            await self.client.stop_notify(char)


class LibraryLink:
    def __init__(self, client, ack, record):
        self.client, self.ack, self.record = client, ack, record
        self._sending = False

    async def send(self, plan, *, response=True, timeout=180, reply_opcode=None):
        if self._sending:
            raise RuntimeError('Only one panel command may be pending.')
        plan.windows = list(plan.windows)
        size = sum(len(window.data) for window in plan.windows)
        limit = 512 if response else self.client.without_response_limit
        plan.chunk_size = min(self.client.chunk_size, limit)
        if not plan.windows or size > 2 * 1024 * 1024 + 4096 or not 1 <= plan.chunk_size <= 512:
            raise ValueError('Plan exceeds bounded library experiment.')
        first = plan.windows[0].data
        image_opcode = first[2] if len(first) >= 15 and first[2:4] in (b'\x02\x00', b'\x03\x00') else None
        if image_opcode is not None:
            self.client.notification_filter = lambda p: len(p) == 5 and p[:4] == bytes((5, 0, image_opcode, 0))
        elif reply_opcode is not None:
            self.client.notification_filter = lambda p: p[2:4] == reply_opcode
        self.client.notifications.clear()  # Retain only this command's replies.
        start = asyncio.get_running_loop().time()
        initial_writes = self.client.write_count
        self._sending = True
        try:
            self.record('library_plan_started', plan=plan.id, windows=len(plan.windows),
                        bytes=size, response=response, chunk_size=plan.chunk_size)
            async with asyncio.timeout(timeout):
                result = await send_plan(self.client, plan, self.ack,
                                         write_with_response=response, ack_timeout=8)
            if not result.success:
                if result.message and 'Timeout' in result.message:
                    raise TimeoutError(result.message)
                raise ValueError(f'Library plan did not succeed: {plan.id}')
            replies = list(self.client.notifications)
            if image_opcode is not None and replies[-1:] != [bytes((5, 0, image_opcode, 0, 3))]:
                raise ValueError('Missing strict final image completion reply.')
            elapsed = asyncio.get_running_loop().time() - start
            self.record('library_plan_completed', plan=plan.id, seconds=round(elapsed, 6),
                        writes=self.client.write_count-initial_writes,
                        replies=[p.hex() for p in replies], response=response)
            return result, elapsed, replies
        except Exception:
            if self.client.notification_error is not None:
                raise self.client.notification_error
            raise
        finally:
            self.client.notification_filter = None
            self._sending = False

    async def query(self, payload, *, opcode, label, timeout=8):
        async def raw_reply(_, data):
            return bytes(data)
        plan = single_window_plan(label, payload, requires_ack=False, response_handler=raw_reply)
        result, _, _ = await self.send(plan, timeout=timeout, reply_opcode=opcode)
        return result.data

    async def initialize(self, *, timezone_name='Europe/Berlin', required_dimensions=(64, 16), versions=True):
        raw = await self.query(device_info_request(datetime.now(ZoneInfo(timezone_name))),
                               opcode=b'\x01\x80', label='device_info_and_clock_sync')
        parsed = parse_device_info(raw)
        self.record('device_info', **parsed)
        if required_dimensions is not None and parsed['reference_dimensions'] != list(required_dimensions):
            raise ValueError('Device type no longer matches the verified panel dimensions.')
        if versions:
            raw_versions = await self.query(build_get_hw_info_command(), opcode=b'\x05\x80', label='firmware_versions')
            self.record('firmware_versions', **parse_versions(raw_versions))
        return upstream_device_info(raw)


@asynccontextmanager
async def library_connection(device, record, *, write_delay=0, chunk_size=244, windows_cached_services=None):
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or not 1 <= chunk_size <= 512:
        raise ValueError('GATT chunk limit must be an integer in 1..512.')
    if windows_cached_services is None:
        windows_cached_services = sys.platform == 'win32'
    if windows_cached_services and sys.platform != 'win32':
        raise ValueError('The Windows cache option is only available on Windows.')
    options = {'winrt_options': {'use_cached_services': True}, 'service_uuids': [SERVICE_UUID]} if windows_cached_services else {}

    def discovered(target):
        details = getattr(target, 'details', None)
        raw = getattr(details, 'adv', None) or getattr(details, 'scan', None)
        record('device_resolved', last_advertisement_rssi_dbm=getattr(raw, 'raw_signal_strength_in_dbm', None))

    record('scan_started', timeout_seconds=15)
    async with connection(device, scan_timeout=15, connect_timeout=30,
                          discovered_callback=discovered, **options) as (_, raw):
        if getattr(raw.services, 'services', None) == {}:
            raise ConnectionError('Bluetooth connected, but the host returned no display services. '
                                  'Check Bluetooth service discovery on this host before reconnecting.')
        write = raw.services.get_characteristic(WRITE_UUID)
        notify = raw.services.get_characteristic(NOTIFY_UUID)
        if not raw.services.get_service(SERVICE_UUID) or write is None or 'write' not in write.properties:
            raise ValueError('Expected 00FA service and FA02 write-with-response absent.')
        if notify is None or 'notify' not in notify.properties or raw.mtu_size < 23:
            raise ValueError('Expected FA03 notifications or valid ATT MTU absent.')
        client = TracedClient(raw, record, write_delay=write_delay)
        client.without_response_limit = write.max_write_without_response_size if 'write-without-response' in write.properties else 0
        client.chunk_size = min(chunk_size, raw.mtu_size-3, 512)
        ack = AckManager()
        await client.start_notify(NOTIFY_UUID, ack.make_notify_handler())
        try:
            record('connected', mtu_size=raw.mtu_size, windows_cached_services=windows_cached_services,
                   backend='pypixelcolor builders and send_plan, instrumented BLE adapter',
                   write_delay_seconds=write_delay, max_write_without_response_size=client.without_response_limit)
            yield LibraryLink(client, ack, record)
        finally:
            if raw.is_connected:
                await client.stop_notify(NOTIFY_UUID)
