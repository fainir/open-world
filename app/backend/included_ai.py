"""Included Claude beta: durable local allowances, never an owner-key fallback.

The central gateway remains the authority for money and cross-process/provider
idempotency. Its transport is deliberately unavailable until its contract lands.
"""
import hashlib
import hmac
import json
import os
import ipaddress
import time
from types import SimpleNamespace
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from datetime import datetime, timedelta
from sqlalchemy import text
from app.backend.auth import SECRET_KEY
from app.backend.models import IncludedCreation

ACTOR_LIMIT = 2
IP_LIMIT = 4
MAX_CONTEXT_BYTES = 768 * 1024
MAX_OUTPUT = 8000
MODEL = 'claude-haiku-5-5'
GATEWAY = 'https://betterloopai.com/api/claude/v1/complete'


class IncludedError(Exception):
    def __init__(self, code, message, *, dispatched=None, status=503):
        super().__init__(message)
        self.code, self.dispatched, self.status = code, dispatched, status


def ready():
    # Default off. Coordinator enables only after the central gate's provenance,
    # spend caps, signed caller and actual creation quality are accepted.
    return os.environ.get('OPENWORLD_INCLUDED_AI_ENABLED') == '1' and len(os.environ.get('JWT_SECRET', '')) >= 32


def digest(kind, value):
    return hmac.new(SECRET_KEY.encode(), ('openworld:' + kind + ':' + value).encode(), hashlib.sha256).hexdigest()


def identities(request, user, guest):
    actor = digest('actor', 'account:' + user.id if user else 'guest:' + guest)
    address = request.client.host if request.client else 'unknown'
    if os.environ.get('RAILWAY_ENVIRONMENT_ID'):
        # Public Railway ingress overwrites this header. Private/internal hosts
        # are outside that contract and may not spend the included allowance.
        if request.url.hostname != 'open-world.gg':
            raise IncludedError('ingress_unavailable', 'Included creation requires the public OpenWorld site.', dispatched=False)
        address = request.headers.get('x-real-ip', '')
        try:
            parsed = ipaddress.ip_address(address)
            address = str(ipaddress.ip_network(str(parsed)+'/64', strict=False)) if parsed.version == 6 else str(parsed)
        except ValueError:
            raise IncludedError('ingress_unavailable', 'Included creation is unavailable on this connection.', dispatched=False)
    return actor, digest('network', address)


def allowance(db, actor, network):
    day = datetime.utcnow() - timedelta(hours=24)
    recent = db.query(IncludedCreation).filter(IncludedCreation.created_at >= day)
    # A proven no-dispatch result releases the actor's funded allowance. The
    # independent network abuse ceiling still counts submitted attempts, bounding
    # repeated paused-budget requests and their private session/file storage.
    return max(0, min(ACTOR_LIMIT - recent.filter(IncludedCreation.actor == actor, IncludedCreation.status != 'rejected').count(),
                      IP_LIMIT - recent.filter(IncludedCreation.network == network).count()))


def reserve(db, request_id, actor, network, payload):
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    # Session reads may have begun a deferred transaction; end it before taking
    # SQLite's write reservation so two processes cannot both pass the quota.
    db.commit()
    db.execute(text('BEGIN IMMEDIATE'))
    try:
        existing = db.get(IncludedCreation, request_id)
        if existing:
            if existing.actor != actor or existing.payload_hash != fingerprint:
                raise IncludedError('request_conflict', 'This request reference belongs to another creation.', dispatched=False, status=409)
            db.commit()
            return existing, False
        if allowance(db, actor, network) < 1:
            raise IncludedError('daily_limit', 'Included creation allowance is used up for this rolling 24-hour window. Play stays free; you can use your own Anthropic key.', dispatched=False, status=429)
        record = IncludedCreation(id=request_id, actor=actor, network=network, payload_hash=fingerprint, status='reserved')
        db.add(record);db.commit()
        return record, True
    except Exception:
        db.rollback();raise


def finish(db, record, status, session_id=None, version_id=None):
    record.status = status
    record.session_id = session_id or record.session_id
    record.version_id = version_id
    db.commit()


def generate(system, messages, *, request_id, actor, network):
    if not isinstance(system, str) or not 1 <= len(messages) <= 12 or any(
        m.get('role') not in ('user', 'assistant') or not isinstance(m.get('content'), str) for m in messages
    ) or messages[-1]['role'] != 'user':
        raise IncludedError('invalid_context', 'This creation cannot use the text-only included beta.', dispatched=False, status=400)
    size = len(system.encode()) + sum(len(m['content'].encode()) for m in messages)
    if size > MAX_CONTEXT_BYTES:
        raise IncludedError('context_limit', 'This game is too large for the included beta. Use your own key for a heavier edit.', dispatched=False, status=413)
    if not ready():
        raise IncludedError('unavailable', 'Included Claude creation is temporarily unavailable. Play stays free; your own key is optional.', dispatched=False)
    from app.backend.portfolio_signing import sign
    payload = {'version': 1, 'app': 'openworld', 'feature': 'generate', 'request_id': request_id,
        'actor': actor, 'actor_ip': network, 'input': {'system': system, 'messages': messages}}
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
    # Bound the complete wire representation too: quotes, newlines and history
    # can make a decoded context exceed the signed profile's byte allowance.
    if len(body) > MAX_CONTEXT_BYTES:
        raise IncludedError('context_limit', 'This game and conversation are too large for the included beta. Use your own key for a heavier edit.', dispatched=False, status=413)
    timestamp = int(time.time())
    request = Request(GATEWAY, data=body, method='POST', headers={
        'Content-Type': 'application/json', 'X-Portfolio-Timestamp': str(timestamp),
        'X-Portfolio-Signature': sign(body, request_id, timestamp),
    })
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):return None
    try:
        try:
            with build_opener(NoRedirect()).open(request, timeout=110) as response:
                status, raw = response.status, response.read(131073)
        except HTTPError as error:
            status, raw = error.code, error.read(8193)
        if len(raw) > (131072 if status == 200 else 8192):raise ValueError('oversized gateway response')
        result = json.loads(raw)
    except Exception:
        raise IncludedError('outcome_unknown', 'The creation result is uncertain. Check saved versions; this reference will not be sent again.')
    if status != 200 or result.get('ok') is not True:
        code = result.get('error', {}).get('code', 'outcome_unknown')
        safe = {
            'invalid_request': 'This request cannot use the included beta. Try a smaller text edit or use your own key.',
            'invalid_signature': 'Included creation is temporarily unavailable. Play stays free.',
            'profile_disabled': 'Included creation is temporarily unavailable. Play stays free; your own key is optional.',
            'quota_exhausted': 'Included creation allowance or shared capacity is currently used up. Play stays free; your own key is optional.',
            'budget_paused': 'The shared beta budget is currently paused. Play stays free; your own key is optional.',
            'unavailable': 'Included creation is temporarily unavailable. Your own key remains optional.',
            'in_progress': 'This creation is still in progress. Check saved versions; do not start duplicate attempts.',
            'request_conflict': 'This creation reference cannot be reused for a different request.',
            'result_expired': 'This creation result is no longer available from the gateway. It will not be charged or generated again.',
            'outcome_unknown': 'The creation result is uncertain. Check saved versions; this reference will not be sent again.',
        }
        # Only the explicit gate proof can release a local allowance. An HTTP
        # error alone says nothing about whether the model was already called.
        dispatched = result.get('dispatched')
        certain_pre_dispatch = code in {'invalid_request', 'invalid_signature', 'profile_disabled',
            'quota_exhausted', 'budget_paused', 'unavailable'}
        if result.get('request_id', request_id) != request_id:certain_pre_dispatch = False
        if dispatched is False and not certain_pre_dispatch:dispatched = None
        if dispatched is not True and dispatched is not False:dispatched = None
        raise IncludedError(code if code in safe else 'outcome_unknown', safe.get(code, safe['outcome_unknown']),
            dispatched=dispatched, status=429 if status == 429 else 409 if status == 409 else 503)
    try:
        if result['request_id'] != request_id or result['model'] != MODEL:raise ValueError()
        content = result['content']
        if not isinstance(content, list) or not content or any(b.get('type') != 'text' or not isinstance(b.get('text'), str) for b in content):raise ValueError()
        return SimpleNamespace(stop_reason=result['stop_reason'], content=[SimpleNamespace(type='text', text=b['text']) for b in content])
    except Exception:
        raise IncludedError('outcome_unknown', 'The creation response could not be confirmed. Check saved versions; no automatic retry will run.')
