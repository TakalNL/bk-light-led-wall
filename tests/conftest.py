"""Synthetic BLE environment: no test accesses an adapter or real device."""

import asyncio
from types import SimpleNamespace

import pytest

from led_matrix_hacker import discovery, transport


def advertisement(address="MOCK-A", name="Mock panel", *, local_name=None, rssi=-42):
    return (
        SimpleNamespace(address=address, name=name),
        SimpleNamespace(
            local_name=local_name, rssi=rssi, service_uuids=["mock-service"],
            manufacturer_data={123: b"\x01\x02"}, service_data={"mock-service": b"\x03"},
        ),
    )


@pytest.fixture(autouse=True)
def ble(monkeypatch):
    characteristic = SimpleNamespace(
        uuid="00001234-0000-1000-8000-00805f9b34fb", handle=7,
        properties=["notify", "write-without-response"], description="Mock data",
        descriptors=[SimpleNamespace(uuid="mock-cccd", handle=8)],
    )

    class Services(list):
        def get_characteristic(self, selector):
            return characteristic if selector in (characteristic.uuid, characteristic.handle) else None

    state = SimpleNamespace(
        advertisements={"MOCK-A": advertisement()}, scan_calls=[], address_find_calls=[], clients=[],
        characteristic=characteristic, messages=[], connect_error=None,
        connect_delay=0, drop_link=False, subscribe_error=None,
    )

    class Scanner:
        @staticmethod
        async def find_device_by_address(device_identifier, *, timeout):
            state.address_find_calls.append({"device_identifier": device_identifier, "timeout": timeout})
            return next((device for device, _ in state.advertisements.values()
                         if device.address.casefold() == device_identifier.casefold()), None)

        @staticmethod
        async def discover(**kwargs):
            state.scan_calls.append(kwargs)
            return state.advertisements

    class Client:
        def __init__(self, device, *, disconnected_callback=None, **options):
            self.device = device
            self.disconnected_callback = disconnected_callback
            self.is_connected = False
            self.calls = []
            self.options = options
            self.services = Services([SimpleNamespace(
                uuid="mock-service", handle=1, description="Mock service",
                characteristics=[characteristic],
            )])
            state.clients.append(self)

        async def connect(self):
            self.calls.append("connect")
            if state.connect_delay:
                await asyncio.sleep(state.connect_delay)
            if state.connect_error:
                raise state.connect_error
            self.is_connected = True

        async def disconnect(self):
            self.calls.append("disconnect")
            self.is_connected = False

        async def start_notify(self, char, callback):
            self.calls.append(("start_notify", char.handle))
            if state.subscribe_error:
                raise state.subscribe_error
            loop = asyncio.get_running_loop()
            for payload in state.messages:
                loop.call_soon(callback, char, bytearray(payload))
            if state.drop_link:
                def drop():
                    self.is_connected = False
                    self.disconnected_callback(self)
                loop.call_soon(drop)

        async def stop_notify(self, char):
            self.calls.append(("stop_notify", char.handle))

        async def write_gatt_char(self, *args, **kwargs):
            pytest.fail("Discovery attempted an application write")

        async def read_gatt_char(self, *args, **kwargs):
            pytest.fail("Metadata inspection attempted a characteristic value read")

        async def write_gatt_descriptor(self, *args, **kwargs):
            pytest.fail("Discovery attempted a direct descriptor write")

    monkeypatch.setattr(discovery, "BleakScanner", Scanner)
    monkeypatch.setattr(transport, "BleakClient", Client)
    return state
