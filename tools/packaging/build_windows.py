"""Build a local standalone preview from a clean wheel-installed environment.

Run this script with the clean environment's Python, not an editable checkout.
The output is a new ZIP; existing artifacts are never replaced or removed.
"""

import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('dist'))
    args = parser.parse_args()
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64'):
        parser.error('Build the Windows x64 bundle on Windows x64.')
    root = Path(__file__).resolve().parents[2]
    installed = metadata.distribution('led-matrix-hacker')
    direct = json.loads(installed.read_text('direct_url.json') or '{}')
    if direct.get('dir_info', {}).get('editable'):
        parser.error('Install the built wheel into a clean virtual environment first.')
    upstream = json.loads(metadata.distribution('pypixelcolor').read_text('direct_url.json') or '{}')
    commit = upstream.get('vcs_info', {}).get('commit_id')
    if upstream.get('dir_info', {}).get('editable') or commit != 'c8cbaebca6df7797a7bcface8a1c4ca33e499973':
        parser.error('Install the pinned pypixelcolor Git revision without editable/local patches.')
    tools = root/'tools'/'packaging'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output/f'LED-Wall-Windows-x64-{installed.version}-preview.zip'
    if archive.exists():
        parser.error(f'Artifact exists; choose another --output directory: {archive}')
    scratch = root/'.tools'/'windows-bundles'
    scratch.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='build-', dir=scratch)).resolve()
    if not work.is_relative_to(root/'.tools'):
        raise ValueError('Build directory must stay within the workspace.')
    command = [sys.executable, '-m', 'PyInstaller', '--onedir', '--name', 'LED-Wall',
               '--distpath', str(work/'dist'), '--workpath', str(work/'work'),
               '--specpath', str(work), '--collect-data', 'led_matrix_hacker',
               '--collect-data', 'tzdata', '--collect-all', 'winrt',
               '--copy-metadata', 'led-matrix-hacker', '--copy-metadata', 'bleak',
               '--exclude-module', 'tkinter', '--exclude-module', 'pytest',
               '--exclude-module', 'playwright', str(tools/'windows_entry.py')]
    subprocess.run(command, cwd=work, check=True)
    bundle = work/'dist'/'LED-Wall'
    shutil.copyfile(tools/'Windows-README.txt', bundle/'READ-ME-FIRST.txt')
    shutil.copyfile(root/'LICENSE', bundle/'LICENSE.txt')
    notices = bundle/'licenses'
    notices.mkdir()
    environment = []
    for dist in sorted(metadata.distributions(), key=lambda d:d.metadata['Name'].lower()):
        name = dist.metadata['Name']
        entry = {'name':name, 'version':dist.version, 'license_files':[]}
        for file in dist.files or ():
            lower = str(file).lower()
            if '.dist-info/' not in lower or not any(word in lower for word in ('license', 'copying', 'notice')):
                continue
            source = Path(dist.locate_file(file))
            if source.is_file():
                target = notices/name/str(file).split('.dist-info/',1)[1]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                entry['license_files'].append(str(target.relative_to(bundle)).replace('\\','/'))
        environment.append(entry)
    python_license = Path(sys.base_prefix)/'LICENSE.txt'
    if not python_license.exists():
        raise FileNotFoundError('Python runtime license is missing; do not distribute the bundle.')
    shutil.copyfile(python_license, notices/'Python-LICENSE.txt')
    info = {'application':installed.version, 'platform':platform.platform(),
            'application_wheel_sha256':direct.get('archive_info',{}).get('hashes',{}).get('sha256'),
            'python':platform.python_version(), 'pypixelcolor_commit':commit,
            'validation':'Local preview; see docs/validation.md. Linux Bluetooth is unverified.',
            'build_environment':environment}
    (bundle/'build-info.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf8')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as zipped:
        for file in sorted(bundle.rglob('*')):
            if file.is_file():zipped.write(file, Path('LED-Wall')/file.relative_to(bundle))
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n',encoding='utf8')
    print('Bundle:',bundle)
    print('Archive:',archive)
    print('SHA256:',digest)


if __name__ == '__main__':
    main()
