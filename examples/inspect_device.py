"""After installation: python examples/inspect_device.py <identifier> --json"""

import sys

from led_matrix_hacker.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["inspect", *sys.argv[1:]]))
