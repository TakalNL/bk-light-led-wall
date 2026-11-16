"""Game output profiles; Windows tuning is optional and scoped to a connection."""

from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
import sys

from led_matrix_hacker.windows_connection import connection_profile


@dataclass(frozen=True)
class StreamingProfile:
    key: str
    label: str
    fps: int


STANDARD = StreamingProfile('standard', 'Standard (10 fps)', 10)
WINDOWS = StreamingProfile('windows-12fps', 'Windows (12 fps)', 12)
PROFILES = {profile.key: profile for profile in (STANDARD, WINDOWS)}


def available_profiles():
    return (STANDARD, WINDOWS) if sys.platform == 'win32' else (STANDARD,)


@asynccontextmanager
async def game_stream_profile(link, key):
    """Fall back before streaming, never retry a failed upload as a fallback."""
    requested = PROFILES[key]
    effective, fallback = STANDARD, None
    async with AsyncExitStack() as scope:
        if requested == WINDOWS:
            if sys.platform != 'win32':
                fallback = 'Windows connection preferences are unavailable on this platform.'
            else:
                try:
                    actual = await scope.enter_async_context(connection_profile(link, 'throughput'))
                except Exception as error:
                    fallback = 'The Windows connection preference is unavailable.'
                    link.record('game_stream_preference_unavailable',
                                error_type=type(error).__name__, message=str(error))
                else:
                    if actual['interval_units'] == 12 and actual['peripheral_latency_events'] == 0:
                        effective = WINDOWS
                    else:
                        # Acceptance alone is insufficient. Release the unused hint.
                        await scope.aclose()
                        fallback = 'The panel did not negotiate the Windows connection preference.'
        link.record('game_stream_profile_ready', requested=requested.key,
                    effective=effective.key, fps=effective.fps, fallback=fallback)
        yield effective, fallback
