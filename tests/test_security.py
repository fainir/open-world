"""Synthetic SQLite/ASGI regressions. No startup seeding, credentials or provider requests."""
import asyncio
import hashlib
import os
from pathlib import Path
import secrets
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

_TEST_ROOT = tempfile.TemporaryDirectory(prefix='openworld-security-')
os.environ['DATA_DIR'] = str(Path(_TEST_ROOT.name) / 'data')
os.environ['VERSIONS_DIR'] = str(Path(_TEST_ROOT.name) / 'versions')
os.environ['JWT_SECRET'] = 'synthetic-openworld-test-secret-32-bytes'
os.environ['SEED_DEMO_STORE'] = '0'
import httpx
from app.backend.database import init_db, SessionLocal
from app.backend.models import User, ChatSession, ChatMessage, GameVersion
from app.backend.auth import create_access_token, hash_api_key
from app.backend.main import app
from app.backend.agent import run_agent


class PrivateAccess(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        init_db()
        self.db = SessionLocal()
        suffix = secrets.token_hex(5)
        self.owner = User(email=suffix+'@owner.invalid', username='owner'+suffix, password_hash='unused')
        self.other = User(email=suffix+'@other.invalid', username='other'+suffix, password_hash='unused')
        self.db.add_all([self.owner, self.other]); self.db.flush()
        self.session = ChatSession(user_id=self.owner.id)
        self.db.add(self.session); self.db.flush()
        self.db.add(ChatMessage(session_id=self.session.id, role='user', content='PRIVATE_SYNTHETIC_CHAT'))
        self.file = Path(os.environ['VERSIONS_DIR']) / (suffix+'.html')
        self.file.write_text('<!doctype html><html><body>PRIVATE_SYNTHETIC_GAME<script>window.onlyGame=true</script></body></html>')
        self.version = GameVersion(session_id=self.session.id, user_id=self.owner.id, version_number=1,
                                   description='PRIVATE_SYNTHETIC_DESCRIPTION', file_path=self.file.name)
        self.db.add(self.version); self.db.commit()
        self.owner_headers = {'Authorization':'Bearer '+create_access_token(self.owner.id)}
        self.other_headers = {'Authorization':'Bearer '+create_access_token(self.other.id)}
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='https://test.invalid')

    async def asyncTearDown(self):
        await self.client.aclose();self.db.close()

    async def test_all_private_reads_require_owner(self):
        for path in ['/api/chat/history/'+self.session.id, '/api/versions/'+self.session.id,
                     '/api/versions/info/'+self.version.id, '/game/version/'+self.version.id]:
            for headers in [{},self.other_headers]:
                with self.subTest(path=path,caller='other' if headers else 'anonymous'):
                    r=await self.client.get(path, headers=headers)
                    self.assertEqual(r.status_code,404);self.assertNotIn('PRIVATE_SYNTHETIC',r.text)
            self.assertEqual((await self.client.get(path,headers=self.owner_headers)).status_code,200)

    async def test_all_private_mutations_require_owner(self):
        for action in ['share','suggest','publish']:
            for headers in [{},self.other_headers]:
                r=await self.client.post('/api/versions/'+action,json={'version_id':self.version.id},headers=headers)
                self.assertIn(r.status_code,[401,404])
        self.db.refresh(self.version)
        self.assertFalse(self.version.is_shared);self.assertFalse(self.version.is_suggested);self.assertFalse(self.version.is_published)

    async def test_cannot_chat_or_branch_private_session(self):
        for body in [{'session_id':self.session.id},{'current_version_id':self.version.id}]:
            with patch('app.backend.main.run_agent') as provider:
                r=await self.client.post('/api/chat',headers=self.other_headers,json={**body,'message':'change title','api_key':'synthetic-key-never-used'})
                self.assertEqual(r.status_code,404);provider.assert_not_called()

    async def test_sharing_exposes_only_game_and_public_metadata(self):
        r=await self.client.post('/api/versions/share',json={'version_id':self.version.id},headers=self.owner_headers)
        self.assertEqual(r.status_code,200);slug=r.json()['share_slug'];self.assertEqual(len(slug),32)
        for path in ['/shared/'+slug,'/game/shared/'+slug,'/game/version/'+self.version.id]:
            r=await self.client.get(path);self.assertEqual(r.status_code,200)
            self.assertIn('sandbox allow-scripts allow-pointer-lock',r.headers['content-security-policy'])
            self.assertNotIn('allow-same-origin',r.headers['content-security-policy'])
            self.assertNotIn('ow_token',r.text);self.assertNotIn('ow_api_key',r.text)
        self.assertEqual((await self.client.get('/api/chat/history/'+self.session.id)).status_code,404)
        self.assertEqual((await self.client.get('/api/versions/'+self.session.id)).status_code,404)

    async def test_studio_document_never_contains_game_code(self):
        r=await self.client.get('/v/'+self.version.id)
        self.assertEqual(r.status_code,200);self.assertIn('sandbox="allow-scripts allow-pointer-lock"',r.text)
        self.assertNotIn('PRIVATE_SYNTHETIC_GAME',r.text);self.assertNotIn('allow-same-origin',r.text)
        self.assertEqual((await self.client.get('/v/'+self.version.id,headers={'If-None-Match':r.headers['etag']})).status_code,304)

    async def test_opaque_or_cross_origin_cannot_call_editor(self):
        for origin in ['null','https://evil.invalid']:
            for method,path,data in [('GET','/api/chat/history/'+self.session.id,None),('POST','/api/versions/share',{'version_id':self.version.id})]:
                r=await self.client.request(method,path,json=data,headers={**self.owner_headers,'Origin':origin})
                self.assertEqual(r.status_code,403)

    async def test_guest_capability_not_public_id_or_other_guest(self):
        token=secrets.token_urlsafe(32)
        guest=ChatSession(guest_access_hash=hashlib.sha256(token.encode()).hexdigest());self.db.add(guest);self.db.commit()
        path='/api/versions/'+guest.id
        for headers in [{},{'X-OpenWorld-Guest':secrets.token_urlsafe(32)},self.owner_headers]:
            self.assertEqual((await self.client.get(path,headers=headers)).status_code,404)
        self.assertEqual((await self.client.get(path,headers={'X-OpenWorld-Guest':token})).status_code,200)

    async def test_legacy_guest_requires_original_key(self):
        key='synthetic-long-key-'+secrets.token_urlsafe(32)
        guest=ChatSession(api_key_hash=hash_api_key(key));self.db.add(guest);self.db.commit()
        path='/api/versions/'+guest.id
        self.assertEqual((await self.client.get(path)).status_code,404)
        self.assertEqual((await self.client.get(path,headers={'X-OpenWorld-Legacy-Key':key})).status_code,200)

    async def test_body_and_model_bounds(self):
        r=await self.client.post('/api/chat',content=b'x'*(8*1024*1024+1))
        self.assertEqual(r.status_code,413)
        r=await self.client.post('/api/chat',json={'message':'x'*8001,'api_key':'synthetic-key'})
        self.assertEqual(r.status_code,422)
        r=await self.client.post('/api/chat',json={'message':'x','api_key':'synthetic-key','image':{'data':'PHN2Zz4=','media_type':'image/svg+xml'}})
        self.assertEqual(r.status_code,422)

    async def test_provider_failure_or_partial_edit_does_not_write_version(self):
        for response in [SimpleNamespace(stop_reason='max_tokens',content=[]),
                         SimpleNamespace(stop_reason='end_turn',content=[SimpleNamespace(type='text',text='<<<SEARCH\nmissing\n===\nreplacement\n>>>SEARCH')])]:
            before=self.db.query(GameVersion).filter_by(session_id=self.session.id).count()
            with patch('app.backend.agent.anthropic.Anthropic') as factory:
                factory.return_value.messages.create.return_value=response
                result=run_agent('synthetic-provider-key','change',self.session,self.db,str(self.file),self.version.id)
                self.assertTrue(result['error']);self.assertEqual(factory.call_args.kwargs['max_retries'],0)
            self.assertEqual(self.db.query(GameVersion).filter_by(session_id=self.session.id).count(),before)

    async def test_success_preserves_previous_version(self):
        response=SimpleNamespace(stop_reason='end_turn',content=[SimpleNamespace(type='text',text='<<<SEARCH\nPRIVATE_SYNTHETIC_GAME\n===\nUPDATED_SYNTHETIC_GAME\n>>>SEARCH\n<description>Changed the title</description><suggestions>["Add trees"]</suggestions>')])
        with patch('app.backend.agent.anthropic.Anthropic') as factory:
            factory.return_value.messages.create.return_value=response
            result=run_agent('synthetic-provider-key','change',self.session,self.db,str(self.file),self.version.id)
        self.assertFalse(result['error']);self.assertIn('PRIVATE_SYNTHETIC_GAME',self.file.read_text())
        path=Path(os.environ['VERSIONS_DIR'])/(result['version_id']+'.html')
        self.assertIn('UPDATED_SYNTHETIC_GAME',path.read_text())
        self.assertEqual(self.db.query(GameVersion).filter_by(id=result['version_id']).one().parent_version_id,self.version.id)

    async def test_recovery_retains_game_files_and_invalidates_old_sessions(self):
        import sqlite3
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        from app.backend.database import get_db, _migrate
        from app.backend.agent import get_base_game_path
        from app.backend.recovery import snapshot, restore
        saved=snapshot(os.environ['DATA_DIR'],os.environ['VERSIONS_DIR'],get_base_game_path())
        self.assertEqual(saved.stat().st_mode & 0o777,0o600)
        dest=Path(_TEST_ROOT.name)/('restored-'+secrets.token_hex(5))
        restore(saved,dest)
        self.assertEqual((dest/'versions'/self.file.name).read_bytes(),self.file.read_bytes())
        engine=create_engine('sqlite:///'+str(dest/'openworld.db'),connect_args={'check_same_thread':False})
        with engine.begin() as conn:conn.execute(text('ALTER TABLE users ADD COLUMN representative_upgrade TEXT'))
        _migrate(engine)
        restored=sessionmaker(bind=engine)()
        def restored_db():yield restored
        app.dependency_overrides[get_db]=restored_db
        try:
            self.assertEqual((await self.client.get('/api/auth/me',headers=self.owner_headers)).status_code,401)
            headers={'Authorization':'Bearer '+create_access_token(self.owner.id,1)}
            r=await self.client.get('/api/chat/history/'+self.session.id,headers=headers)
            self.assertEqual(r.status_code,200);self.assertIn('PRIVATE_SYNTHETIC_CHAT',r.text)
            self.assertEqual(restored.execute(text('SELECT count(*) FROM chat_sessions WHERE guest_access_hash IS NOT NULL OR api_key_hash IS NOT NULL')).scalar(),0)
        finally:
            app.dependency_overrides.clear();restored.close();engine.dispose()

    async def test_recovery_rejects_corruption_and_missing_game(self):
        import zipfile
        from app.backend.recovery import snapshot, restore
        from app.backend.agent import get_base_game_path
        saved=snapshot(os.environ['DATA_DIR'],os.environ['VERSIONS_DIR'],get_base_game_path())
        corrupt=Path(_TEST_ROOT.name)/('corrupt-'+secrets.token_hex(5)+'.zip')
        with zipfile.ZipFile(saved) as original,zipfile.ZipFile(corrupt,'w') as altered:
            for name in original.namelist():altered.writestr(name,b'corrupted' if name=='base.html' else original.read(name))
        dest=Path(_TEST_ROOT.name)/('bad-restore-'+secrets.token_hex(5))
        with self.assertRaises(RuntimeError):restore(corrupt,dest)
        self.assertFalse(dest.exists())
        content=self.file.read_bytes();self.file.unlink()
        try:
            with self.assertRaises(RuntimeError):snapshot(os.environ['DATA_DIR'],os.environ['VERSIONS_DIR'],get_base_game_path())
            self.assertEqual((await self.client.get('/healthz')).status_code,503)
        finally:self.file.write_bytes(content)


if __name__=='__main__':unittest.main(verbosity=2)
