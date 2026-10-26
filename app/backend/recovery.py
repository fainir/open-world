"""Verified SQLite + immutable game-file snapshots and offline restore.

Snapshots contain private accounts and chat. Store them with owner-only permissions.
No HTTP download or restore endpoint is exposed.
"""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import threading
import time
import zipfile

PUBLICATION_LOCK = threading.RLock()


def _digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def snapshot(data_dir, versions_dir, base_path):
    data_dir, versions_dir, base_path = map(Path, (data_dir, versions_dir, base_path))
    directory = data_dir / 'recovery'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    target = directory / ('snapshot-' + str(time.time_ns()) + '.zip')
    with PUBLICATION_LOCK, tempfile.TemporaryDirectory(dir=directory) as temporary:
        root = Path(temporary);os.chmod(root, 0o700)
        backup_path = root / 'openworld.db'
        with closing(sqlite3.connect(f'file:{data_dir / "openworld.db"}?mode=ro', uri=True)) as source, closing(sqlite3.connect(backup_path)) as dest:
            source.backup(dest)
        os.chmod(backup_path, 0o600)
        with closing(sqlite3.connect(backup_path)) as db:
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise RuntimeError('Database snapshot failed verification')
            files = [row[0] for row in db.execute('SELECT DISTINCT file_path FROM game_versions')]
        manifest = {'format': 1, 'createdAt': time.time(), 'files': {}}
        staged = {'openworld.db': backup_path, 'base.html': base_path}
        for name in files:
            if Path(name).name != name or not name.endswith('.html'):
                raise RuntimeError('Invalid game path in database')
            staged['versions/' + name] = versions_dir / name
        for name, path in staged.items():
            if not path.is_file() or path.is_symlink():
                raise RuntimeError('Referenced game file is missing')
            manifest['files'][name] = {'sha256': _digest(path), 'bytes': path.stat().st_size}
        partial = target.with_suffix('.partial')
        try:
            with zipfile.ZipFile(partial, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, path in staged.items():archive.write(path, name)
                archive.writestr('manifest.json', json.dumps(manifest))
            os.chmod(partial, 0o600)
            verify(partial)
            os.replace(partial, target)
        finally:
            partial.unlink(missing_ok=True)
    for old in sorted(directory.glob('snapshot-*.zip'))[:-7]:old.unlink()
    return target


def verify(archive_path):
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('format') != 1 or not isinstance(manifest.get('files'), dict):
            raise RuntimeError('Unsupported snapshot')
        if set(archive.namelist()) != set(manifest['files']) | {'manifest.json'}:
            raise RuntimeError('Snapshot manifest mismatch')
        total = 0
        for name, record in manifest['files'].items():
            if name not in ['openworld.db', 'base.html'] and not (name.startswith('versions/') and len(Path(name).parts) == 2 and name.endswith('.html') and '..' not in Path(name).parts):
                raise RuntimeError('Invalid snapshot path')
            info = archive.getinfo(name);total += info.file_size
            if info.file_size != record['bytes'] or total > 2 * 1024**3:
                raise RuntimeError('Snapshot size mismatch')
            with archive.open(name) as source:
                if hashlib.file_digest(source, 'sha256').hexdigest() != record['sha256']:
                    raise RuntimeError('Snapshot checksum mismatch')
        if 'openworld.db' not in manifest['files'] or 'base.html' not in manifest['files']:
            raise RuntimeError('Incomplete snapshot')
        return manifest


def restore(archive_path, destination):
    """Restore into a NEW private directory, with all old sessions invalidated."""
    manifest = verify(archive_path)
    destination = Path(destination)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for name in manifest['files']:
                path = destination / name;path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with archive.open(name) as source, path.open('wb') as output:
                    shutil.copyfileobj(source, output, length=1024*1024)
                os.chmod(path, 0o600)
        with closing(sqlite3.connect(destination / 'openworld.db')) as db:
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':raise RuntimeError('Restore verification failed')
            columns = {row[1] for row in db.execute('PRAGMA table_info(users)')}
            if 'auth_revision' not in columns:db.execute('ALTER TABLE users ADD COLUMN auth_revision INTEGER NOT NULL DEFAULT 0')
            db.execute('UPDATE users SET auth_revision = auth_revision + 1')
            columns = {row[1] for row in db.execute('PRAGMA table_info(chat_sessions)')}
            if 'guest_access_hash' not in columns:db.execute('ALTER TABLE chat_sessions ADD COLUMN guest_access_hash VARCHAR')
            db.execute('UPDATE chat_sessions SET guest_access_hash=NULL, api_key_hash=NULL')
            db.commit()
            for (name,) in db.execute('SELECT DISTINCT file_path FROM game_versions'):
                if not (destination / 'versions' / name).is_file():raise RuntimeError('Restored game file missing')
    except Exception:
        shutil.rmtree(destination)
        raise
    return manifest


def health(data_dir):
    directory = Path(data_dir) / 'recovery'
    files = sorted(directory.glob('snapshot-*.zip'))
    if not files:return {'ok': False, 'ageSeconds': None}
    age = time.time() - files[-1].stat().st_mtime
    return {'ok': age < 48 * 3600, 'ageSeconds': round(age)}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['verify', 'restore'])
    parser.add_argument('snapshot')
    parser.add_argument('--destination')
    args = parser.parse_args()
    if args.action == 'restore':
        if not args.destination:parser.error('--destination is required')
        restore(args.snapshot, args.destination)
    else:verify(args.snapshot)
    print(json.dumps({'ok': True, 'action': args.action}))
