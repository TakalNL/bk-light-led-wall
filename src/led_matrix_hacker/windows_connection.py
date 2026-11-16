"""Scoped Windows BLE connection preferences shared by games and experiments.

Bleak does not expose this request publicly. Keep private WinRT access here,
and let callers decide whether an unavailable preference is fatal. No request
is made until the context is entered; every acquired request is released.
"""

import asyncio
from contextlib import asynccontextmanager


def connection_snapshot(device):
    parameters = device.get_connection_parameters()
    interval = int(parameters.connection_interval)
    if interval <= 0:
        raise ValueError('Windows reports no active connection parameters.')
    return dict(interval_units=interval, interval_ms=interval * 1.25,
                peripheral_latency_events=int(parameters.connection_latency),
                supervision_timeout_ms=int(parameters.link_timeout) * 10)


@asynccontextmanager
async def connection_profile(link, profile, *, preferred=None, settle_seconds=5):
    if profile not in ('default', 'throughput'):
        raise ValueError('Unknown Windows connection profile.')
    device = getattr(getattr(link.client, '_backend', None), '_requester', None)
    if device is None or not hasattr(device, 'get_connection_parameters'):
        raise RuntimeError('The connected Bleak Windows backend does not expose this API.')
    before = connection_snapshot(device)
    link.record('windows_parameters_before', **before)
    request = None
    try:
        if profile == 'throughput':
            if preferred is None:
                from winrt.windows.devices.bluetooth import BluetoothLEPreferredConnectionParameters
                preferred = BluetoothLEPreferredConnectionParameters.throughput_optimized
            request = device.request_preferred_connection_parameters(preferred)
            link.record('windows_preference_requested', status=int(request.status),
                        min_interval_ms=preferred.min_connection_interval * 1.25,
                        max_interval_ms=preferred.max_connection_interval * 1.25,
                        peripheral_latency_events=int(preferred.connection_latency))
            if int(request.status) != 1:  # Microsoft enum: SUCCESS = accepted by system.
                raise RuntimeError('Windows did not accept the connection preference request.')
            deadline = asyncio.get_running_loop().time() + settle_seconds
            previous = before
            while True:
                actual = connection_snapshot(device)
                if actual != previous:
                    link.record('windows_parameters_changed', **actual)
                    previous = actual
                matches = (preferred.min_connection_interval <= actual['interval_units']
                           <= preferred.max_connection_interval
                           and actual['peripheral_latency_events'] <= preferred.connection_latency)
                if matches or asyncio.get_running_loop().time() >= deadline:
                    break
                await asyncio.sleep(.1)
        else:
            await asyncio.sleep(.25)
            actual, matches = connection_snapshot(device), None
        link.record('windows_profile_ready', profile=profile, negotiated_matches_request=matches, **actual)
        yield actual
        link.record('windows_parameters_after_stream', **connection_snapshot(device))
    finally:
        if request is not None:
            request.close()
            link.record('windows_preference_released')


