# Shared game infrastructure

`app.py` provides `GameApp`: the desktop preview, controls, settings, pause/focus
handling, update loop and connection UI. Each game's `app.py` supplies its rules,
renderer, PNG encoder, status and keyboard handling.

`panel.py` provides the latest-state mailbox and a single Bluetooth worker. It
requires the game's encoder explicitly and uses the shared `library_link.py`
pypixelcolor backend for profile checks and uploads. All games share the existing target setting in
`captures/snake-settings.json` for compatibility, with separate log prefixes.

## Panel update profiles

All three games have a **Panel updates** selector. Choose a profile while
disconnected, then connect. The choice is remembered with the panel target and
is shared between games. Existing settings use **Standard (10 fps)**.

- **Standard (10 fps)** keeps the existing connection and upload behaviour.
- **Windows (12 fps)** requests the scoped Windows throughput preference before
  streaming. It targets 12 uploads/second only when Windows accepts the request
  and reports a 15-ms connection interval with no peripheral latency. If the
  API is unavailable, the request is refused, or negotiation does not match
  within five seconds, the game uses Standard and shows the fallback in its
  connection status. The requested choice remains saved for the next connection.

The Windows option is offered only on Windows. It uses a private Bleak WinRT
object, so availability depends on the Windows version and Bluetooth backend.
The request is released on disconnect, connection cancellation or stream error;
every reconnect makes a new request. Windows may negotiate other parameters
later, so the initial check is not a guarantee for the whole session. The
throughput preference can reduce the radio's simultaneous connection capacity.

Both profiles use acknowledged writes, up to 500-byte chunks limited by the
negotiated MTU, complete RGB PNGs in non-saving slot 0, and one image in flight.
The worker keeps only the latest unsent state. Profile selection changes panel
output pacing, not game speed. Windows mode uses fixed scheduling deadlines to
avoid accumulating sleep overshoot, and skips elapsed slots instead of queuing
old states. Standard keeps its existing minimum interval between upload starts.
Fast writes and timer-resolution changes remain experiment-only. The target is
a scheduled upload rate, not measured physical refresh or a guaranteed rate.

The shared Windows request implementation is in
`src/led_matrix_hacker/windows_connection.py`; the standalone experiment reuses
it. See [Windows connection tests](../../WINDOWS_CONNECTION_TESTS.md) and
[transport/pacing tests](../../WINDOWS_TRANSPORT_PACING_TESTS.md) for the hardware
evidence behind the option. The integration checks cover fallback, negotiation,
cancelled uploads, reconnects and selected-rate pacing. A desktop smoke check
verified the selector and fallback status in all three games.
The [app integration record](../../GAME_STREAMING_PROFILE_TESTS.md) contains
the worker/reconnect checks and owner observations.

## Finding the saved panel

Saved Bluetooth addresses (or macOS UUID identifiers) use Bleak's address
lookup, which stops scanning as soon as the matching advertisement arrives.
The 15-second discovery timeout is an upper bound rather than a fixed wait for
these identifiers. A missing identifier reports the normal device-not-found
error without starting another scan or selecting a different device by name.

Exact-name searches still use the full scan window to reject duplicate names.
Connection and initialization follow discovery, so radio/advertising delays
can still affect the total time. Two checks on the owner's Windows setup became
ready in 1.56 and 2.91 seconds, compared with about 16 seconds before this change.
