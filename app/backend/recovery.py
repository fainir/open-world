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


DELETIONS_FILE = 'deleted-accounts.json'
RESTORE_CONTRACT_VERSION = 2


def needs_restore_drill(previous, snapshot_sha, target_exists):
    """A changed restore contract requires a real drill even for the same archive."""
    previous=previous if isinstance(previous,dict) else {}
    return (not target_exists or previous.get('sha256')!=snapshot_sha
            or previous.get('restoreContract')!=RESTORE_CONTRACT_VERSION
            or previous.get('restoreDrillPassed') is not True or not previous.get('restoreDrillAt'))


def _validate_deleted_accounts(value):
    if not isinstance(value, dict) or value.get('format') != 1 or not isinstance(value.get('accounts'), list):
        raise RuntimeError('Invalid account-deletion evidence')
    ids = value['accounts']
    if len(ids) > 1_000_000 or any(not isinstance(item, str) or not 1 <= len(item) <= 100 for item in ids):
        raise RuntimeError('Invalid account-deletion evidence')
    return set(ids)


def write_deleted_accounts(data_dir, ids):
    """Private durable intent, independent of the SQLite transaction being removed."""
    directory = Path(data_dir);directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = directory / DELETIONS_FILE
    if target.is_symlink():raise RuntimeError('Invalid account-deletion evidence path')
    payload = json.dumps({'format': 1, 'accounts': sorted(set(ids))})
    _validate_deleted_accounts(json.loads(payload))
    handle, temporary = tempfile.mkstemp(prefix='.deletions-', dir=directory)
    try:
        with os.fdopen(handle, 'w') as output:
            output.write(payload);output.flush();os.fsync(output.fileno())
        os.chmod(temporary, 0o600);os.replace(temporary, target)
        descriptor=os.open(directory,os.O_RDONLY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_deleted_accounts(data_dir, create=False):
    target = Path(data_dir) / DELETIONS_FILE
    if not target.exists() and create:write_deleted_accounts(data_dir, set())
    if target.is_symlink() or target.stat().st_size > 128 * 1024**2:
        raise RuntimeError('Invalid account-deletion evidence path or size')
    return _validate_deleted_accounts(json.loads(target.read_text()))


def snapshot_deleted_accounts(archive_path):
    """The current-snapshot mirror drill carries that snapshot's deletion evidence."""
    with zipfile.ZipFile(archive_path) as archive:
        if DELETIONS_FILE not in archive.namelist():return set() # Before account closure existed.
        return _validate_deleted_accounts(json.loads(archive.read(DELETIONS_FILE)))


def purge_account(connection, user_id):
    """Delete only this account's rows; returns its now-unreferenced game filenames."""
    owned = 'SELECT id FROM game_versions WHERE session_id IN (SELECT id FROM chat_sessions WHERE user_id=?)'
    args=(user_id,)
    names=[row[0] for row in connection.execute('SELECT DISTINCT file_path FROM game_versions WHERE id IN ('+owned+')',args)]
    if any(Path(name).name != name or not name.endswith('.html') for name in names):
        raise RuntimeError('Invalid owned game path')
    columns={row[1] for row in connection.execute('PRAGMA table_info(game_versions)')}
    if 'parent_version_id' in columns:
        connection.execute('UPDATE game_versions SET parent_version_id=NULL WHERE parent_version_id IN ('+owned+')',args)
    if 'reviewed_by' in columns:
        connection.execute('UPDATE game_versions SET reviewed_by=NULL WHERE reviewed_by=?',(user_id,))
    connection.execute('UPDATE game_versions SET user_id=(SELECT user_id FROM chat_sessions WHERE chat_sessions.id=game_versions.session_id) WHERE user_id=? AND id NOT IN ('+owned+')',(user_id,*args))
    connection.execute('DELETE FROM stars WHERE user_id=? OR version_id IN ('+owned+')',(user_id,*args))
    connection.execute('DELETE FROM game_versions WHERE id IN ('+owned+')',args)
    connection.execute('DELETE FROM chat_messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE user_id=?)',(user_id,))
    connection.execute('DELETE FROM chat_sessions WHERE user_id=?',(user_id,))
    connection.execute('DELETE FROM users WHERE id=?',(user_id,))
    return [name for name in names if not connection.execute('SELECT 1 FROM game_versions WHERE file_path=? LIMIT 1',(name,)).fetchone()]


def reconcile_deleted_accounts(data_dir, versions_dir, ids=None):
    """Apply surviving intent before startup snapshots or any restored service traffic."""
    data_dir,versions_dir=Path(data_dir),Path(versions_dir)
    ids=read_deleted_accounts(data_dir,create=True) if ids is None else set(ids)
    database=data_dir/'openworld.db'
    if not database.exists():return
    with PUBLICATION_LOCK, closing(sqlite3.connect(database)) as connection:
        connection.execute('BEGIN IMMEDIATE')
        names=set()
        for user_id in ids:names.update(purge_account(connection,user_id))
        connection.commit()
        for name in names:(versions_dir/name).unlink(missing_ok=True)
        for user_id in ids:
            directory=data_dir/'account-removals'/hashlib.sha256(user_id.encode()).hexdigest()
            if directory.is_dir() and not directory.is_symlink():shutil.rmtree(directory)


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
        read_deleted_accounts(data_dir,create=True)
        staged = {'openworld.db': backup_path, 'base.html': base_path, DELETIONS_FILE: data_dir/DELETIONS_FILE}
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
            if name not in ['openworld.db', 'base.html', DELETIONS_FILE] and not (name.startswith('versions/') and len(Path(name).parts) == 2 and name.endswith('.html') and '..' not in Path(name).parts):
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


def restore(archive_path, destination, *, deletions=None):
    """Restore into a NEW private directory, with all old sessions invalidated."""
    if deletions is None:raise RuntimeError('Current account-deletion evidence is required for restore')
    manifest = verify(archive_path)
    deletions=set(deletions) | snapshot_deleted_accounts(archive_path)
    destination = Path(destination)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for name in manifest['files']:
                path = destination / name;path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with archive.open(name) as source, path.open('wb') as output:
                    shutil.copyfileobj(source, output, length=1024*1024)
                os.chmod(path, 0o600)
        write_deleted_accounts(destination,deletions)
        reconcile_deleted_accounts(destination,destination/'versions',deletions)
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
    evidence=Path(data_dir)/DELETIONS_FILE
    reconciled=not evidence.exists() or evidence.stat().st_mtime <= files[-1].stat().st_mtime
    return {'ok': age < 48 * 3600 and reconciled, 'ageSeconds': round(age), 'deletionsBackedUp': reconciled}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['verify', 'restore'])
    parser.add_argument('snapshot')
    parser.add_argument('--destination')
    parser.add_argument('--deletions',help='Current surviving deleted-accounts.json, not an older snapshot copy')
    args = parser.parse_args()
    if args.action == 'restore':
        if not args.destination:parser.error('--destination is required')
        if not args.deletions:parser.error('--deletions with current surviving evidence is required')
        evidence=Path(args.deletions)
        if evidence.name!=DELETIONS_FILE:parser.error('--deletions must name the current deleted-accounts.json file')
        restore(args.snapshot, args.destination,deletions=read_deleted_accounts(evidence.parent))
    else:verify(args.snapshot)
    print(json.dumps({'ok': True, 'action': args.action}))
