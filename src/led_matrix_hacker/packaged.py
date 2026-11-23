"""User-directory defaults for the standalone Windows launcher."""

import os
from pathlib import Path
import sys


def arguments(argv):
    data = Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData'/'Local'))/'LED Wall'
    defaults = {'--host': '0.0.0.0', '--settings': str(data/'wall-settings.json'),
                '--capture-dir': str(data/'captures')}
    result = []
    for name, value in defaults.items():
        if not any(arg == name or arg.startswith(name+'=') for arg in argv):
            result.extend((name, value))
    if not any(arg in ('--open', '--no-open') for arg in argv):
        result.append('--open')
    return result + list(argv)


def main():
    from .server import main as serve
    serve(arguments(sys.argv[1:]))


if __name__ == '__main__':
    main()
