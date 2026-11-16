"""Panel preferences shared by the three game launchers."""

import json

from .profiles import PROFILES, STANDARD


def load_panel_settings(path):
    try:
        saved = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        saved = {}
    if not isinstance(saved, dict):
        saved = {}
    device = saved.get('device', '')
    profile = saved.get('stream_profile')
    return {
        'device': device if isinstance(device, str) else '',
        'stream_profile': profile if isinstance(profile, str) and profile in PROFILES else STANDARD.key,
    }


def save_panel_settings(path, *, device, profile):
    if profile not in PROFILES:
        raise ValueError('Unknown game streaming profile.')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'device': device, 'stream_profile': profile})+'\n', encoding='utf-8')
