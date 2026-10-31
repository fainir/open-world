"""Purpose-separated signing from the existing server secret; no saved new key."""
import base64
import hashlib
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _key():
    secret = os.environ.get('JWT_SECRET', '')
    if len(secret) < 32:raise ValueError('Stable server signing secret is unavailable')
    seed = HKDF(algorithm=hashes.SHA256(), length=32, salt=b'',
                info=b'portfolio-claude/v1/openworld').derive(secret.encode())
    return Ed25519PrivateKey.from_private_bytes(seed)


def _b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


def public_key():
    return _b64(_key().public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo))


def sign(body, request_id, timestamp):
    canonical = '\n'.join(['portfolio-claude/v1', 'POST', '/api/claude/v1/complete',
        'openworld', 'generate', request_id, str(timestamp), hashlib.sha256(body).hexdigest()])
    return _b64(_key().sign(canonical.encode()))
