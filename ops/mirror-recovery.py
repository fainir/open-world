"""Copy verified server snapshots into a private, encrypted independent mirror.

Installed beside recovery.py and mirror-config.json; never logs account contents.
Uses an explicitly pinned official Railway CLI with the owner's existing login.
"""
from pathlib import Path
import base64
import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import secrets
import shlex
import sqlite3
import subprocess
import tempfile
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent
AAD = b'openworld-recovery-v1'
MAX_ARCHIVE = 256 * 1024 * 1024


def atomic_private(path, data):
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=ROOT)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def run():
    os.umask(0o077)
    ROOT.chmod(0o700)
    with (ROOT / 'mirror.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'skipped': 'another mirror check is running'}))
            return
        config = json.loads((ROOT / 'mirror-config.json').read_text())
        for field in ('project', 'environment', 'service'):
            if not re.fullmatch(r'[a-f0-9-]{36}', config[field]):
                raise RuntimeError('Invalid Railway target')
        spec = importlib.util.spec_from_file_location('snapshot_recovery', ROOT / 'recovery.py')
        recovery = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recovery)
        key_path = ROOT / 'recovery.key'
        if not key_path.exists():
            with key_path.open('xb') as output:
                output.write(secrets.token_bytes(32))
        key_path.chmod(0o600)
        cipher = AESGCM(key_path.read_bytes())
        remote = '''import os,json,base64,hashlib,pathlib,re,time
d=pathlib.Path(os.environ.get('DATA_DIR','/app/app/data'))/'recovery'
files=sorted(p for p in d.glob('snapshot-*.zip') if re.fullmatch(r'snapshot-[0-9]+\\.zip',p.name))
if not files:raise RuntimeError('No server snapshot')
p=files[-1]
if p.is_symlink() or p.stat().st_size>256*1024*1024:raise RuntimeError('Invalid snapshot')
with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
print(json.dumps({'name':p.name,'sha256':digest,'bytes':p.stat().st_size}),flush=True)
with p.open('rb') as f:
 while chunk:=f.read(16384):
  print(base64.b64encode(chunk).decode(),flush=True)
  time.sleep(.005)
'''
        command = [config['railway'], 'ssh', '--project', config['project'],
                   '--environment', config['environment'], '--service', config['service'],
                   shlex.join(['python', '-c', remote])]
        with tempfile.TemporaryDirectory(prefix='.copy-', dir=ROOT) as temporary:
            archive = Path(temporary) / 'snapshot.zip'
            # Capture privately; never allow remote output or account contents into logs.
            result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=150)
            if result.returncode:
                raise RuntimeError('Railway snapshot transfer failed; check the existing CLI login')
            lines = result.stdout.splitlines()
            metadata = json.loads(lines[0])
            if not re.fullmatch(r'snapshot-[0-9]+\.zip', metadata['name']):
                raise RuntimeError('Invalid snapshot name')
            if not 0 < metadata['bytes'] <= MAX_ARCHIVE:
                raise RuntimeError('Snapshot exceeds the mirror size limit')
            digest = hashlib.sha256()
            copied = 0
            with archive.open('xb') as output:
                for line in lines[1:]:
                    chunk = base64.b64decode(line, validate=True)
                    copied += len(chunk)
                    if copied > MAX_ARCHIVE:
                        raise RuntimeError('Snapshot exceeds the mirror size limit')
                    output.write(chunk)
                    digest.update(chunk)
            if copied != metadata['bytes'] or digest.hexdigest() != metadata['sha256']:
                raise RuntimeError('Snapshot transfer checksum mismatch')
            manifest = recovery.verify(archive)
            age = time.time() - manifest['createdAt']
            if not -300 < age < 48 * 3600:
                raise RuntimeError('Server snapshot is stale or its clock is invalid')
            target = ROOT / (metadata['name'] + '.aesgcm')
            previous = json.loads((ROOT / 'status.json').read_text()) if (ROOT / 'status.json').exists() else {}
            drill = previous.get('sha256') != metadata['sha256'] or not target.exists()
            if drill:
                recovery.restore(archive, Path(temporary) / 'restored', deletions=recovery.snapshot_deleted_accounts(archive))
                db = sqlite3.connect(Path(temporary) / 'restored/openworld.db')
                try:
                    if db.execute('SELECT count(*) FROM users WHERE auth_revision < 1').fetchone()[0]:
                        raise RuntimeError('Restored account sessions were not invalidated')
                    if db.execute('SELECT count(*) FROM chat_sessions WHERE api_key_hash IS NOT NULL OR guest_access_hash IS NOT NULL').fetchone()[0]:
                        raise RuntimeError('Restored guest credentials were not invalidated')
                    db.execute('ALTER TABLE game_versions ADD COLUMN mirror_restore_drill TEXT')
                    db.commit()
                    if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                        raise RuntimeError('Restored database failed integrity check')
                finally:
                    db.close()
            plaintext = archive.read_bytes()
            # Authenticate existing ciphertext too; preserve the original encryption key.
            if target.exists():
                encrypted = target.read_bytes()
                if cipher.decrypt(encrypted[:12], encrypted[12:], AAD) != plaintext:
                    raise RuntimeError('Existing encrypted copy differs from server snapshot')
            else:
                nonce = secrets.token_bytes(12)
                encrypted = nonce + cipher.encrypt(nonce, plaintext, AAD)
                if cipher.decrypt(encrypted[:12], encrypted[12:], AAD) != plaintext:
                    raise RuntimeError('Encrypted copy verification failed')
                atomic_private(target, encrypted)
            target.chmod(0o600)
            for old in sorted(ROOT.glob('snapshot-*.zip.aesgcm'))[:-7]:
                old.unlink()
            status = {'checkedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'snapshotCreatedAt': manifest['createdAt'], 'snapshotAgeSeconds': round(age),
                      'sha256': metadata['sha256'], 'snapshot': metadata['name'],
                      'encryptedCopyVerified': True, 'restoreDrillPassed': True,
                      'restoreDrillRanThisCheck': drill,
                      'restoreDrillAt': datetime.datetime.now(datetime.timezone.utc).isoformat() if drill else previous['restoreDrillAt'],
                      'scope': 'Independent encrypted Mac copy; runs only while this Mac is awake and its Railway login works.'}
            atomic_private(ROOT / 'status.json', (json.dumps(status, indent=2) + '\n').encode())
            print(json.dumps(status))


if __name__ == '__main__':
    try:
        run()
    except Exception as error:
        # Error classes are enough for unattended diagnostics; never log remote data.
        print(json.dumps({'ok': False, 'errorType': type(error).__name__,
                          'message': str(error) if type(error) is RuntimeError else 'Mirror check failed'}))
        raise SystemExit(1)
