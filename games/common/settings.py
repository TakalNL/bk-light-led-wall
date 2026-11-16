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


def load_or_migrate_panel_settings(path, legacy_path):
    """Import the old capture-local preference once without replacing new settings."""
    if not path.exists() and legacy_path.is_file():
        saved = load_panel_settings(legacy_path)
        save_panel_settings(path, device=saved['device'], profile=saved['stream_profile'])
    return load_panel_settings(path)
