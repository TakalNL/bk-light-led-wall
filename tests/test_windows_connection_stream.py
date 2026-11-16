import asyncio
from types import SimpleNamespace

import pytest

from examples.windows_connection_stream import (
    MeasuredSleep, connection_profile, connection_snapshot, send_png, timer_precision,
)
from examples.png_pipeline_stream import marker_png


class Device:
    def __init__(self, *, status=1, negotiate=True):
        self.parameters = SimpleNamespace(connection_interval=18, connection_latency=0, link_timeout=200)
        self.request = SimpleNamespace(status=status, close=self.close)
        self.closed = self.requests = 0
        self.negotiate = negotiate

    def close(self):
        self.closed += 1

    def get_connection_parameters(self):
        return self.parameters

    def request_preferred_connection_parameters(self, preferred):
        self.requests += 1
        if self.negotiate:
            self.parameters = SimpleNamespace(connection_interval=12, connection_latency=0, link_timeout=200)
        return self.request


def run_profile(device, profile='throughput', *, fail=False):
    records = []
    link = SimpleNamespace(client=SimpleNamespace(_backend=SimpleNamespace(_requester=device)),
                           record=lambda kind, **fields: records.append((kind, fields)))
    preferred = SimpleNamespace(min_connection_interval=12, max_connection_interval=12, connection_latency=0)
    async def run():
        async with connection_profile(link, profile, preferred=preferred, settle_seconds=0) as actual:
            if fail:
                raise OSError('stream failed')
            return actual
    return run, records


def test_connection_units_are_converted_and_inactive_connection_is_rejected():
    device = Device()
    assert connection_snapshot(device) == dict(interval_units=18, interval_ms=22.5,
                                               peripheral_latency_events=0, supervision_timeout_ms=2000)
    device.parameters.connection_interval = 0
    with pytest.raises(ValueError, match='no active'):
        connection_snapshot(device)


def test_accepted_preference_is_scoped_and_actual_parameters_are_recorded():
    device = Device()
    run, records = run_profile(device)
    actual = asyncio.run(run())
    assert actual['interval_ms'] == 15 and device.requests == device.closed == 1
    ready = next(fields for kind, fields in records if kind == 'windows_profile_ready')
    assert ready['negotiated_matches_request']
    assert records[-1][0] == 'windows_preference_released'


def test_acceptance_does_not_imply_negotiation():
    device = Device(negotiate=False)
    run, records = run_profile(device)
    assert asyncio.run(run())['interval_ms'] == 22.5
    ready = next(fields for kind, fields in records if kind == 'windows_profile_ready')
    assert not ready['negotiated_matches_request'] and device.closed == 1


@pytest.mark.parametrize('status', [0, 2, 3])
def test_rejected_request_is_closed_without_running_stream(status):
    device = Device(status=status)
    run, records = run_profile(device)
    with pytest.raises(RuntimeError, match='did not accept'):
        asyncio.run(run())
    assert device.closed == 1
    assert not any(kind == 'windows_profile_ready' for kind, fields in records)


def test_request_is_released_when_stream_fails():
    device = Device()
    run, _ = run_profile(device, fail=True)
    with pytest.raises(OSError, match='stream failed'):
        asyncio.run(run())
    assert device.closed == 1


def test_default_profile_does_not_request_a_change():
    device = Device()
    run, _ = run_profile(device, 'default')
    assert asyncio.run(run())['interval_ms'] == 22.5
    assert device.requests == device.closed == 0


class TimerApi:
    def __init__(self, *, begin_status=0, end_status=0):
        self.calls = []
        self.begin_status, self.end_status = begin_status, end_status

    def timeBeginPeriod(self, period):
        self.calls.append(('begin', period))
        return self.begin_status

    def timeEndPeriod(self, period):
        self.calls.append(('end', period))
        return self.end_status


def test_timer_request_is_released_with_matching_period_after_failure():
    api = TimerApi()
    with pytest.raises(OSError, match='stream failed'):
        with timer_precision(1, lambda *a, **kw: None, api=api):
            raise OSError('stream failed')
    assert api.calls == [('begin', 1), ('end', 1)]


def test_default_timing_makes_no_request():
    api = TimerApi()
    with timer_precision(None, lambda *a, **kw: None, api=api):
        pass
    assert api.calls == []


def test_rejected_timer_request_is_not_claimed_or_released():
    api = TimerApi(begin_status=97)
    records = []
    with pytest.raises(RuntimeError, match='rejected'):
        with timer_precision(1, lambda *a, **kw: records.append((a, kw)), api=api):
            pytest.fail('Rejected timer request entered its scope')
    assert api.calls == [('begin', 1)] and not records


def test_timer_release_failure_is_reported():
    api = TimerApi(end_status=97)
    records = []
    with pytest.raises(RuntimeError, match='release failed'):
        with timer_precision(1, lambda kind, **kw: records.append((kind, kw)), api=api):
            pass
    assert api.calls == [('begin', 1), ('end', 1)]
    assert records[-1] == ('timer_precision_released', {'requested_ms': 1, 'release_status': 97})


def test_boolean_is_not_accepted_as_a_timer_period():
    api = TimerApi()
    with pytest.raises(ValueError):
        with timer_precision(True, lambda *a, **kw: None, api=api):
            pass
    assert api.calls == []


def test_wait_measurement_preserves_requested_sleep_and_counts_lateness():
    now, requested, records = [0.0], [], []
    async def underlying(delay):
        requested.append(delay)
        now[0] += delay + .002
    async def run():
        sleep = MeasuredSleep(lambda kind, **kw: records.append((kind, kw)),
                              clock=lambda: now[0], sleep=underlying)
        await sleep(.008)
        await sleep(0)
        await sleep(.004)
        return sleep.summary()
    result = asyncio.run(run())
    assert requested == [.008, 0, .004]
    assert result['positive_waits'] == 2 and result['zero_waits'] == 1
    assert result['overshoot_ms']['median'] == 2
    assert len(records) == 2


@pytest.mark.parametrize('fast', [False, True])
def test_png_write_mode_preserves_upstream_completion_waits(fast):
    calls = []
    async def send(plan, **options):
        calls.append((plan, options))
    link = SimpleNamespace(client=SimpleNamespace(chunk_size=500, without_response_limit=244), send=send)
    png = marker_png('END', 1)
    asyncio.run(send_png(link, None, png, fast=fast))
    plan, options = calls[0]
    assert options == {'response': not fast, 'timeout': 4}
    assert plan.ack_policy.ack_per_window and plan.ack_policy.ack_final
    assert plan.windows[0].data[15:] == png and plan.windows[0].data[14] == 0


def test_fast_png_limit_is_checked_before_any_write():
    calls = []
    async def send(*args, **kwargs):
        calls.append((args, kwargs))
    link = SimpleNamespace(client=SimpleNamespace(chunk_size=500, without_response_limit=20), send=send)
    with pytest.raises(ValueError, match='fitting one supported write'):
        asyncio.run(send_png(link, None, marker_png('END', 1), fast=True))
    assert calls == []
