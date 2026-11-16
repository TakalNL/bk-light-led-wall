"""Create and verify a private ZIP plus a per-file SHA-256 manifest.

This tool never deletes source files. Paths in the archive are workspace-relative.
"""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def digest(stream):
    result = hashlib.sha256()
    size = 0
    while chunk := stream.read(262144):
        result.update(chunk)
        size += len(chunk)
    return result.hexdigest(), size


def archive(root, destination, sources, *, exclude=()):
    root = root.resolve()
    destination = destination.resolve()
    destination.relative_to(root)
    excluded = {(root/path).resolve() for path in exclude}
    files = set()
    for source in sources:
        path = (root/source).resolve()
        path.relative_to(root)
        if not path.exists():
            raise FileNotFoundError(source)
        for item in path.rglob('*') if path.is_dir() else (path,):
            resolved = item.resolve()
            resolved.relative_to(root)
            if item.is_file() and resolved not in excluded:
                files.add(resolved)
    if destination.exists() or destination.with_suffix('.manifest.json').exists():
        raise FileExistsError('Use a new archive name; existing archives are preserved.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with ZipFile(destination, 'x', compression=ZIP_DEFLATED, compresslevel=6) as output:
        for path in sorted(files):
            if path == destination:
                raise ValueError('An archive cannot contain itself.')
            relative = path.relative_to(root).as_posix()
            before = path.stat()
            with path.open('rb') as original:
                sha, size = digest(original)
            output.write(path, relative)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise RuntimeError(f'Source changed during archiving: {relative}')
            records.append({'path': relative, 'bytes': size, 'sha256': sha})
    with ZipFile(destination) as saved:
        if len(saved.infolist()) != len(records):
            raise ValueError('Archive member count disagrees with manifest.')
        for record in records:
            with saved.open(record['path']) as member:
                sha, size = digest(member)
            if (sha, size) != (record['sha256'], record['bytes']):
                raise ValueError(f'Archive verification failed: {record["path"]}')
    with destination.open('rb') as saved:
        sha, size = digest(saved)
    manifest = {'archive': destination.relative_to(root).as_posix(),
                'archive_sha256': sha, 'archive_bytes': size,
                'original_bytes': sum(row['bytes'] for row in records),
                'verified': True, 'files': records}
    destination.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    return {key: value for key, value in manifest.items() if key != 'files'} | {'file_count': len(records)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('sources', nargs='+')
    parser.add_argument('--exclude', action='append', default=[])
    args = parser.parse_args()
    print(json.dumps(archive(Path.cwd(), args.destination, args.sources, exclude=args.exclude)))


if __name__ == '__main__':
    main()
