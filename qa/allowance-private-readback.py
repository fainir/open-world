"""Read only the exact synthetic renewal edit and its parent, never guest proofs."""
import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path
from app.backend.game_security import game_response

data = Path(os.environ['DATA_DIR'])
versions = Path(os.environ.get('VERSIONS_DIR', str(data / 'versions')))
with sqlite3.connect(f'file:{data / "openworld.db"}?mode=ro', uri=True) as db:
    db.row_factory = sqlite3.Row
    row = db.execute('''select c.id,c.status,c.created_at,v.version_number,
        v.is_shared,v.is_published,v.user_id,v.file_path,p.file_path as parent_file
        from included_creations c join game_versions v on v.id=c.version_id
        join game_versions p on p.id=v.parent_version_id where c.id=?''',
        ('0ccc586b-67ae-48a5-9f70-0a950263ed7e',)).fetchone()
    assert row and row['status'] == 'complete'
    assert row['user_id'] is None and not row['is_shared'] and not row['is_published']
    generated = (versions / row['file_path']).read_bytes()
    parent = (versions / row['parent_file']).read_bytes()
    base = Path(os.environ.get('BASE_GAME_PATH', str(data / 'base.html'))).read_bytes()
    scripts = lambda html: re.findall(rb'<script\b[^>]*>.*?</script>', html, re.S | re.I)
    assert scripts(generated) == scripts(parent)
    assert b'Guest trial verified' in generated
    print(json.dumps({'request_id': row['id'], 'status': row['status'],
        'created_at': row['created_at'], 'version_number': row['version_number'],
        'guest': True, 'shared': False, 'published': False,
        'badge_saved': True, 'original_script_blocks_unchanged': len(scripts(parent)),
        'parent_matches_public_base': parent == base,
        'added_bytes': len(generated) - len(parent),
        'public_base_sha256': hashlib.sha256(base).hexdigest(),
        'public_response_sha256': hashlib.sha256(game_response(
            os.environ.get('BASE_GAME_PATH', str(data / 'base.html'))).body).hexdigest()}, indent=2))
