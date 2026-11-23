"""Standalone defaults must work independently of the launch directory."""
from led_matrix_hacker.packaged import arguments


def test_packaged_defaults_use_user_storage_and_allow_cli_overrides(monkeypatch,tmp_path):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'profile'))
    defaults = arguments([])
    assert str(tmp_path/'profile'/'LED Wall'/'wall-settings.json') in defaults
    assert str(tmp_path/'profile'/'LED Wall'/'captures') in defaults
    assert '--open' in defaults and '0.0.0.0' in defaults
    supplied = ['--settings=custom.json','--capture-dir','logs','--host','127.0.0.1','--no-open']
    assert arguments(supplied) == supplied
