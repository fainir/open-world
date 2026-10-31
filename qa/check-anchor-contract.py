"""Offline exact-source/wire check; refuses before any model or game write."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
message = 'Add a small always-visible badge at the upper-right that says Synthetic QA. Keep all gameplay, controls and other text unchanged.'

with tempfile.TemporaryDirectory(prefix='openworld-anchor-contract-') as scratch:
    data = Path(scratch)
    safe = {'HOME': os.environ.get('HOME', '/Users/nirfeinstein'), 'PATH': '/usr/bin:/bin:/usr/local/bin',
            'DATA_DIR': str(data/'data'), 'VERSIONS_DIR': str(data/'versions'),
            'JWT_SECRET': 'synthetic-anchor-check-secret-at-least-32-characters', 'SEED_DEMO_STORE': '0'}
    os.environ.clear();os.environ.update(safe);sys.path.insert(0, str(ROOT))
    from app.backend.agent import run_agent, _minify_game_code
    original = (ROOT/'index.html').read_text()
    class Captured(Exception):pass
    def inspect(system, messages):
        shown = messages[-1]['content']
        assert '<current_game_code>\n' + original + '\n</current_game_code>' in shown
        payload = {'version': 1, 'app': 'openworld', 'feature': 'generate',
                   'request_id': '00000000-0000-4000-8000-000000000001', 'actor': 'a'*64, 'actor_ip': 'b'*64,
                   'input': {'system': system, 'messages': messages}}
        body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
        assert len(body) <= 768*1024
        mismatch = next((line for line in original.splitlines() if line.strip() and _minify_game_code(line)
                         and original.count(_minify_game_code(line)) == 0), None)
        assert mismatch is not None
        print(json.dumps({'fixture': 'tracked full original game', 'source_utf8': len(original.encode()),
                          'full_signed_envelope_utf8': len(body), 'wire_limit': 768*1024,
                          'exact_source_shown': True, 'legacy_prompt_anchor_original_matches': 0,
                          'provider_requests': 0, 'game_writes': 0}))
        raise Captured()
    try:
        run_agent('', message, SimpleNamespace(messages=[SimpleNamespace(role='user', content=message)]), None,
                  current_version_path=str(ROOT/'index.html'), included_provider=inspect)
    except Captured:pass
    else:raise AssertionError('Inspection did not stop before generation/publication')
