"""After installation: python examples/scan.py --timeout 15 --json"""

import sys

from led_matrix_hacker.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["scan", *sys.argv[1:]]))
