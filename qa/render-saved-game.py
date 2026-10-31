"""Read-only loopback studio for one recovered genuine synthetic QA artifact."""
import argparse
import json
import os
from pathlib import Path
import socket
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser();parser.add_argument('artifact');args = parser.parse_args()
artifact = Path(args.artifact).resolve()
assert artifact.is_file() and not (artifact.stat().st_mode & 0o077) and artifact.stat().st_size < 4*1024*1024
with tempfile.TemporaryDirectory(prefix='openworld-saved-artifact-render-') as temporary:
    scratch = Path(temporary)
    safe = {'HOME': os.environ.get('HOME', '/Users/nirfeinstein'), 'PATH': '/usr/bin:/bin:/usr/local/bin',
            'LANG': 'C', 'DATA_DIR': str(scratch/'data'), 'VERSIONS_DIR': str(scratch/'versions'),
            'BASE_GAME_PATH': str(artifact), 'JWT_SECRET': 'synthetic-render-only-secret-at-least-32-characters',
            'SEED_DEMO_STORE': '0', 'OPENWORLD_INCLUDED_AI_ENABLED': '0'}
    os.environ.clear();os.environ.update(safe);os.chdir(ROOT);sys.path.insert(0, str(ROOT))
    from app.backend.main import app
    from fastapi.responses import JSONResponse
    @app.middleware('http')
    async def read_only(request, call_next):
        if request.method not in ('GET', 'HEAD'):
            return JSONResponse({'detail': 'Read-only genuine-artifact rendering; no generation or account action'}, status_code=503)
        return await call_next(request)
    sock = socket.socket();sock.bind(('127.0.0.1', 0));sock.listen()
    print('ARTIFACT_RENDER ' + json.dumps({'base': 'http://127.0.0.1:' + str(sock.getsockname()[1]),
          'scope': 'actual saved model/parser HTML in unchanged local studio sandbox', 'model_requests': 0, 'accounts': 0}), flush=True)
    import uvicorn
    config = uvicorn.Config(app, host='127.0.0.1', port=sock.getsockname()[1], access_log=False, log_level='warning')
    try:uvicorn.Server(config).run(sockets=[sock])
    finally:sock.close()
