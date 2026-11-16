"""Session summaries, with optional full packet capture for diagnostics."""

import json
import time

from .discovery import utc_now


class Recorder:
    def __init__(self, output, *, echo=True, trace_packets=True):
        self.output = output
        self.echo = echo
        self.trace_packets = trace_packets
        self.started = time.monotonic()

    def __call__(self, kind, **fields):
        if not self.trace_packets and kind in {
            'library_write_attempt', 'library_write_completed', 'library_notification',
            'library_plan_started', 'library_plan_completed',
        }:
            return
        row = {"timestamp": utc_now(), "elapsed_seconds": round(time.monotonic() - self.started, 6),
               "kind": kind, **fields}
        self.output.write(json.dumps(row) + "\n")
        self.output.flush()
        # Keep full packet bytes in the private capture; large image data is noisy on stdout.
        visible = dict(row)
        if len(visible.get("payload_hex", "")) > 128:
            visible["payload_hex"] = visible["payload_hex"][:128] + "... (full bytes in capture)"
        if self.echo:
            print(json.dumps(visible), flush=True)
