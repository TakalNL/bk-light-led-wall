"""Shared command-line startup and Tk error handling for the game launchers."""

import argparse
import logging
from pathlib import Path
import tkinter as tk


def launch_game(app_class, *, description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--device', default='')
    parser.add_argument('--connect', action='store_true')
    parser.add_argument('--preview', action='store_true', help='Play locally without Bluetooth.')
    parser.add_argument('--capture-dir', type=Path, default=Path('captures'))
    parser.add_argument('--settings', type=Path, default=Path('.state/panel-settings.json'))
    parser.add_argument('--trace-packets', action='store_true', help='Record full BLE packets for diagnostics.')
    args = parser.parse_args()
    args.capture_dir.mkdir(parents=True, exist_ok=True)
    error_log = args.capture_dir/f'{app_class.log_name}-errors.log'
    logging.basicConfig(filename=error_log, level=logging.ERROR)
    root = tk.Tk()

    def callback_error(error_type, value, traceback):
        logging.error('%s UI error', app_class.heading, exc_info=(error_type, value, traceback))
        app.game.pause()
        app.connection_status.set(f'An app error occurred; see {error_log.name}.')

    root.report_callback_exception = callback_error
    app = app_class(root, capture_dir=args.capture_dir, settings_path=args.settings,
                    device=args.device, connect=args.connect, preview=args.preview,
                    trace_packets=args.trace_packets)
    root.mainloop()
