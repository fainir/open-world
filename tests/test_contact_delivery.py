"""Owned synthetic inbox/outbox only. All notification transports are mocked."""
import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid
import test_security  # installs the existing disposable SQLite environment first
import httpx
from sqlalchemy import create_engine, text
from app.backend.database import init_db, SessionLocal, Base, _migrate
from app.backend.models import ContactMessage, User
from app.backend.main import app
from app.backend.auth import create_access_token
from app.backend import contact_delivery as delivery
from app.backend.request_limits import _buckets

class ContactOutbox(unittest.TestCase):
    def setUp(self):
        init_db();_buckets.clear()
        with SessionLocal() as db:db.query(ContactMessage).delete();db.commit()
    def add(self, **values):
        with SessionLocal() as db:
            message=ContactMessage(name='Synthetic',email='synthetic@example.test',message='Synthetic no-mail check',notification_key=str(uuid.uuid4()),notification_status='queued',**values)
            db.add(message);db.commit();return message.id
    def row(self,id):
        with SessionLocal() as db:return db.get(ContactMessage,id)
    def test_accepted_is_durable_and_never_sent_twice(self):
        id=self.add();reference=str(uuid.uuid4())
        with patch.object(delivery,'relay_send',return_value=('accepted',reference,0)) as send:
            delivery.deliver(id);delivery.deliver(id);delivery.sweep()
        self.assertEqual(send.call_count,1);row=self.row(id);self.assertEqual(row.notification_reference,reference);self.assertEqual(row.notification_attempts,1)
        self.assertEqual(send.call_args.args[1]['product'],'openworld');self.assertEqual(send.call_args.args[0],row.notification_key)
    def test_concurrent_claims_send_only_once(self):
        from concurrent.futures import ThreadPoolExecutor
        import time
        id=self.add()
        def accept(*args):time.sleep(.05);return 'accepted',str(uuid.uuid4()),0
        with patch.object(delivery,'relay_send',side_effect=accept) as send:
            with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(delivery.deliver,[id,id]))
        self.assertEqual(send.call_count,1);self.assertEqual(self.row(id).notification_attempts,1)
    def test_timeout_keeps_key_and_backoff_across_retry(self):
        id=self.add()
        with patch.object(delivery,'relay_send',side_effect=TimeoutError) as send:delivery.deliver(id)
        row=self.row(id);key=row.notification_key;self.assertEqual(row.notification_status,'retry');self.assertEqual(row.notification_error,'transport_unknown')
        with patch.object(delivery,'relay_send') as send:delivery.deliver(id);send.assert_not_called()
        with SessionLocal() as db:db.get(ContactMessage,id).notification_next_at=datetime.utcnow()-timedelta(seconds=1);db.commit()
        with patch.object(delivery,'relay_send',return_value=('accepted',str(uuid.uuid4()),0)) as send:delivery.sweep()
        self.assertEqual(send.call_args.args[0],key);self.assertEqual(self.row(id).notification_status,'accepted')
    def test_uncertain_receipt_and_old_attempt_park_without_resend(self):
        id=self.add()
        with patch.object(delivery,'relay_send',return_value=('review','delivery_uncertain',0)) as send:delivery.deliver(id);delivery.sweep()
        self.assertEqual(send.call_count,1);self.assertEqual(self.row(id).notification_status,'review')
        old=self.add(notification_attempts=1,created_at=datetime.utcnow()-timedelta(hours=21))
        with patch.object(delivery,'relay_send') as send:delivery.deliver(old);send.assert_not_called()
        self.assertEqual(self.row(old).notification_status,'review')
    def test_max_attempts_stop_and_interrupted_claim_reuses_key(self):
        id=self.add(notification_attempts=4)
        with patch.object(delivery,'relay_send',return_value=('retry','relay_unavailable',60)):delivery.deliver(id)
        self.assertEqual(self.row(id).notification_status,'review')
        other=self.add()
        with SessionLocal() as db:
            row=db.get(ContactMessage,other);row.notification_status='sending';row.notification_attempts=1;row.notification_last_at=datetime.utcnow()-timedelta(seconds=120);db.commit()
        key=self.row(other).notification_key
        with patch.object(delivery,'relay_send',return_value=('accepted',str(uuid.uuid4()),0)) as send:delivery.sweep()
        self.assertEqual(send.call_args.args[0],key)
    def test_migration_keeps_historical_inbox_and_never_backfills(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=create_engine('sqlite:///'+folder+'/old.db');Base.metadata.create_all(engine)
            with engine.begin() as db:
                db.execute(text('DROP TABLE contact_messages'))
                db.execute(text('CREATE TABLE contact_messages(id VARCHAR PRIMARY KEY,name VARCHAR NOT NULL,email VARCHAR NOT NULL,message TEXT NOT NULL,is_read BOOLEAN,created_at DATETIME)'))
                db.execute(text("INSERT INTO contact_messages VALUES('old','Historical','old@example.test','HISTORICAL_MESSAGE',1,CURRENT_TIMESTAMP)"))
            _migrate(engine);_migrate(engine)
            with engine.connect() as db:
                row=db.execute(text('SELECT name,message,is_read,notification_status,notification_key,notification_attempts FROM contact_messages')).one()
                self.assertEqual(tuple(row),('Historical','HISTORICAL_MESSAGE',1,'legacy',None,0))
            engine.dispose()
        with SessionLocal() as db:
            row=ContactMessage(name='Old',email='old@example.test',message='Never backfill');db.add(row);db.commit()
        with patch.object(delivery,'relay_send') as send:delivery.sweep();send.assert_not_called()
    def test_relay_headers_fixed_recipient_route_and_uncertain_classification(self):
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):return json.dumps({'ok':True,'reference':str(uuid.uuid4())}).encode()
        with patch.object(delivery,'urlopen',return_value=Response()) as send:
            self.assertEqual(delivery.relay_send(str(uuid.uuid4()),{'product':'openworld'})[0],'accepted')
        request=send.call_args.args[0];self.assertEqual(request.full_url,delivery.RELAY);self.assertEqual(request.get_header('Origin'),'https://open-world.gg');self.assertEqual(send.call_args.kwargs['timeout'],25)
        from urllib.error import HTTPError
        import io
        error=HTTPError(delivery.RELAY,503,'unavailable',{},io.BytesIO(b'{"ok":false,"code":"delivery_uncertain"}'))
        with patch.object(delivery,'urlopen',side_effect=error):self.assertEqual(delivery.relay_send('key',{})[:2],('review','delivery_uncertain'))
        error=HTTPError(delivery.RELAY,429,'limited',{'Retry-After':'600'},io.BytesIO(b'{"ok":false,"error":"rate_limited"}'))
        with patch.object(delivery,'urlopen',side_effect=error):self.assertEqual(delivery.relay_send('key',{}),('retry','relay_busy',600))
    def test_submission_payload_bound_duplicate_and_no_transport(self):
        async def check():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test.invalid') as client:
                key=str(uuid.uuid4());payload={'name':'Synthetic','email':'synthetic@example.test','message':'PRIVATE_DRAFT'};headers={'Idempotency-Key':key}
                with patch.object(delivery,'relay_send') as send:
                    for _ in range(2):self.assertEqual((await client.post('/api/contact',json=payload,headers=headers)).json(),{'status':'stored','notification':'queued'})
                    send.assert_not_called()
                with SessionLocal() as db:self.assertEqual(db.query(ContactMessage).count(),1)
                conflict=await client.post('/api/contact',json={**payload,'message':'changed'},headers=headers);self.assertEqual(conflict.status_code,409)
                invalid=await client.post('/api/contact',json={**payload,'email':'a@b.com?subject=unsafe'});self.assertEqual(invalid.status_code,400)
                self.assertEqual((await client.post('/api/contact',content='x'*32769)).status_code,413)
                self.assertEqual((await client.get('/api/admin/contacts')).status_code,401)
                response=await client.post('/contact',content='message=PRIVATE_DRAFT');self.assertEqual(response.status_code,503);self.assertNotIn('PRIVATE_DRAFT',response.text)
        asyncio.run(check())
    def test_admin_retry_stays_private_and_review_is_not_resendable(self):
        id=self.add()
        with SessionLocal() as db:
            admin=User(email=str(uuid.uuid4())+'@example.test',username=str(uuid.uuid4()),password_hash='unused',is_admin=True);db.add(admin);db.commit();token=create_access_token(admin.id)
            row=db.get(ContactMessage,id);row.notification_status='review';row.notification_error='delivery_uncertain';db.commit()
        async def check():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test.invalid') as client:
                self.assertEqual((await client.post('/api/admin/contacts/'+id+'/retry')).status_code,401)
                headers={'Authorization':'Bearer '+token}
                self.assertEqual((await client.post('/api/admin/contacts/'+id+'/retry',headers=headers)).status_code,409)
                result=(await client.get('/api/admin/contacts',headers=headers)).json()[0];self.assertEqual(result['notification_status'],'review');self.assertEqual(result['notification_error'],'delivery_uncertain')
                self.assertEqual((await client.post('/api/admin/contacts/'+id+'/read',headers=headers)).status_code,200)
        asyncio.run(check())
