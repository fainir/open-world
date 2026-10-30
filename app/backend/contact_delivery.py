"""Durable, bounded owner notifications. No historical inbox backfill or visitor mail."""
import json
import os
import threading
import uuid
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from sqlalchemy import or_
from app.backend.database import SessionLocal
from app.backend.models import ContactMessage

RELAY = 'https://betterloopai.com/api/public/contact'
MAX_ATTEMPTS = 5
_stop = threading.Event()
_wake = threading.Event()
_thread = None


def relay_send(key, payload):
    request = Request(RELAY, data=json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode(), method='POST', headers={
        'Content-Type': 'application/json', 'Origin': 'https://open-world.gg',
        'Idempotency-Key': key,
    })
    try:
        with urlopen(request, timeout=25) as response:
            status, data, retry = response.status, response.read(16385), None
    except HTTPError as error:
        status, data, retry = error.code, error.read(16385), error.headers.get('Retry-After')
    result = json.loads(data) if len(data) <= 16384 else {}
    if status == 200 and result.get('ok') is True:
        reference = str(uuid.UUID(result.get('reference', '')))
        return 'accepted', reference, 0
    code = result.get('code') or result.get('error')
    if code in ('delivery_uncertain', 'key_conflict'):
        return 'review', str(code), 0
    if status in (400, 403, 413, 415):
        return 'review', 'relay_rejected', 0
    try:
        delay = max(60, min(86400, int(retry or 60)))
    except (ValueError, TypeError):
        delay = 60
    return 'retry', 'relay_busy' if status in (409, 429) else 'relay_unavailable', delay


def deliver(contact_id):
    now = datetime.utcnow()
    with SessionLocal() as db:
        message = db.get(ContactMessage, contact_id)
        if not message or message.notification_status not in ('queued', 'retry'):
            return
        if message.notification_next_at and message.notification_next_at > now:
            return
        # Provider idempotency is time bounded. Old unknown attempts need a human
        # receipt check instead of creating another email after that boundary.
        if message.notification_attempts >= MAX_ATTEMPTS or (message.notification_attempts and now - message.created_at > timedelta(hours=20)):
            message.notification_status = 'review';message.notification_error = 'receipt_review_required';db.commit();return
        claimed = db.query(ContactMessage).filter(ContactMessage.id == contact_id,
            ContactMessage.notification_status.in_(('queued', 'retry'))).update({
                ContactMessage.notification_status: 'sending',
                ContactMessage.notification_attempts: ContactMessage.notification_attempts + 1,
                ContactMessage.notification_last_at: now,
            }, synchronize_session=False)
        if claimed != 1:
            db.rollback();return
        payload = {'product': 'openworld', 'name': message.name, 'email': message.email,
                   'message': message.message, 'website': ''}
        key = message.notification_key
        db.commit()
    try:
        state, detail, delay = relay_send(key, payload)
    except Exception:
        # A timeout may have accepted mail. Keep exactly the same key on retry.
        state, detail, delay = 'retry', 'transport_unknown', 60
    with SessionLocal() as db:
        message = db.get(ContactMessage, contact_id)
        if not message or message.notification_status != 'sending':return
        message.notification_status = state
        message.notification_reference = detail if state == 'accepted' else None
        message.notification_error = None if state == 'accepted' else detail
        if state == 'retry':
            if message.notification_attempts >= MAX_ATTEMPTS:
                message.notification_status = 'review'
            else:
                message.notification_next_at = datetime.utcnow() + timedelta(seconds=max(delay, [60, 300, 1800, 7200][min(message.notification_attempts - 1, 3)]))
        db.commit()


def sweep():
    now = datetime.utcnow()
    with SessionLocal() as db:
        # Recover interrupted claims using their existing key, never a fresh send.
        db.query(ContactMessage).filter(ContactMessage.notification_status == 'sending',
            ContactMessage.notification_last_at < now - timedelta(seconds=90)).update({
                ContactMessage.notification_status: 'retry', ContactMessage.notification_next_at: now,
                ContactMessage.notification_error: 'interrupted_attempt',
            }, synchronize_session=False)
        db.commit()
        ids = [m.id for m in db.query(ContactMessage).filter(
            ContactMessage.notification_status.in_(('queued', 'retry')),
            or_(ContactMessage.notification_next_at.is_(None), ContactMessage.notification_next_at <= now)
        ).order_by(ContactMessage.created_at).limit(8)]
    for contact_id in ids:
        if _stop.is_set():break
        deliver(contact_id)


def wake():
    _wake.set()


def start():
    global _thread
    # Local fixtures/tests never send. Production can explicitly pause delivery.
    if not os.environ.get('RAILWAY_ENVIRONMENT_ID') or os.environ.get('CONTACT_NOTIFICATIONS_ENABLED') == '0':return
    if _thread and _thread.is_alive():return
    _stop.clear()
    def loop():
        while not _stop.is_set():
            try:sweep()
            except Exception:pass  # durable queue survives; never log private payloads
            _wake.wait(30);_wake.clear()
    _thread = threading.Thread(target=loop, daemon=True, name='openworld-contact')
    _thread.start()


def stop():
    _stop.set();_wake.set()
