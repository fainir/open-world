import asyncio
import os
import time
from collections import OrderedDict, deque

from fastapi.responses import JSONResponse

_buckets = OrderedDict()


async def boundaries(request, call_next):
    path = request.url.path
    if path.startswith('/api/'):
        origin = request.headers.get('origin')
        allowed = set(os.environ.get('STUDIO_ORIGINS', 'https://open-world.gg').split(','))
        allowed.add(str(request.base_url).rstrip('/'))
        if origin and origin not in allowed:
            return JSONResponse({'detail': 'Studio origin required'}, status_code=403)
        address = request.client.host if request.client else 'unknown'
        if os.environ.get('RAILWAY_ENVIRONMENT_ID'):
            address = request.headers.get('x-real-ip') or address
        category, limit, window = ('read', 180, 60)
        if request.method != 'GET':
            category, limit, window = ('write', 60, 60)
        if path.startswith('/api/auth/') and request.method == 'POST':
            category, limit, window = ('auth', 20, 3600)
        elif path in ('/api/chat', '/api/chat/idea'):
            category, limit, window = ('generation', 10, 3600)
        elif path == '/api/contact':
            category, limit, window = ('contact', 5, 3600)
        key = (address, category)
        now = time.monotonic()
        bucket = _buckets.pop(key, deque())
        while bucket and bucket[0] <= now - window:
            bucket.popleft()
        _buckets[key] = bucket
        while len(_buckets) > 10_000:
            _buckets.popitem(last=False)
        if len(bucket) >= limit:
            return JSONResponse({'detail': 'Please try again later'}, status_code=429,
                                headers={'Retry-After': str(window)})
        bucket.append(now)
        if request.method == 'POST':
            try:
                chunks = []
                size = 0
                async with asyncio.timeout(15):
                    async for chunk in request.stream():
                        size += len(chunk)
                        if size > (32 * 1024 if path == '/api/contact' else 8 * 1024 * 1024):
                            return JSONResponse({'detail': 'Request too large'}, status_code=413)
                        chunks.append(chunk)
                request._body = b''.join(chunks)
            except TimeoutError:
                return JSONResponse({'detail': 'Request timed out'}, status_code=408)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response
