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
        restore(saved,dest,deletions=set())
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
        with self.assertRaises(RuntimeError):restore(corrupt,dest,deletions=set())
        self.assertFalse(dest.exists())
        content=self.file.read_bytes();self.file.unlink()
        try:
            with self.assertRaises(RuntimeError):snapshot(os.environ['DATA_DIR'],os.environ['VERSIONS_DIR'],get_base_game_path())
            self.assertEqual((await self.client.get('/healthz')).status_code,503)
        finally:self.file.write_bytes(content)




class AccountRights(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await PrivateAccess.asyncSetUp(self)
        from app.backend.auth import hash_password
        self.password='Synthetic-account-password-2026'
        self.owner.password_hash=hash_password(self.password)
        self.foreign_session=ChatSession(user_id=self.other.id)
        self.db.add(self.foreign_session);self.db.flush()
        self.foreign_file=Path(os.environ['VERSIONS_DIR'])/('foreign-'+secrets.token_hex(8)+'.html')
        self.foreign_file.write_text('<!doctype html><html>OTHER_PRIVATE_GAME</html>')
        self.foreign_version=GameVersion(session_id=self.foreign_session.id,user_id=self.other.id,version_number=1,description='OTHER_PRIVATE_DESCRIPTION',file_path=self.foreign_file.name,parent_version_id=self.version.id)
        self.db.add(self.foreign_version);self.db.commit()
        from app.backend.request_limits import _buckets
        _buckets.clear()
        from app.backend.accounts import _ACCOUNT_BUCKETS
        _ACCOUNT_BUCKETS.clear()

    async def asyncTearDown(self):
        await PrivateAccess.asyncTearDown(self)

    async def close_account(self,**changes):
        return await self.client.post('/api/account/delete',headers=self.owner_headers,json={'password':self.password,'confirm':'DELETE',**changes})

    async def test_export_contains_only_account_owned_data_and_real_game_files(self):
        import io,json,zipfile
        # A stale denormalized user field does not grant access to another session.
        self.foreign_version.user_id=self.owner.id;self.db.commit()
        for headers in [{},self.other_headers]:
            response=await self.client.get('/api/account/export',headers=headers)
            if not headers:self.assertEqual(response.status_code,401)
            else:self.assertNotIn('PRIVATE_SYNTHETIC_CHAT',response.text)
        response=await self.client.get('/api/account/export',headers=self.owner_headers)
        self.assertEqual(response.status_code,200);self.assertEqual(response.headers['cache-control'],'no-store')
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            payload=json.loads(archive.read('account.json'))
            self.assertEqual(payload['profile']['email'],self.owner.email)
            self.assertEqual(len(payload['sessions']),1);self.assertEqual(len(payload['versions']),1)
            self.assertEqual(archive.read('games/'+self.version.id+'.html'),self.file.read_bytes())
            self.assertNotIn('games/'+self.foreign_version.id+'.html',archive.namelist())
            text=json.dumps(payload)
            for forbidden in ['password_hash','auth_revision','api_key_hash','guest_access_hash','OTHER_PRIVATE','access_token']:
                self.assertNotIn(forbidden,text)
        self.assertEqual(list((Path(os.environ['DATA_DIR'])/'exports').glob('export-*.zip')),[])

    async def test_closure_requires_current_password_exact_confirmation_and_same_origin(self):
        self.assertEqual((await self.close_account(password='wrong')).status_code,400)
        self.assertEqual((await self.close_account(confirm='delete')).status_code,400)
        self.assertEqual((await self.client.post('/api/account/delete',headers={**self.owner_headers,'Origin':'https://unrelated.invalid'},json={'password':self.password,'confirm':'DELETE'})).status_code,403)
        self.assertEqual((await self.client.post('/api/account/delete',json={'password':self.password,'confirm':'DELETE'})).status_code,401)
        self.assertTrue(self.file.exists());self.assertIsNotNone(self.db.get(User,self.owner.id))

    async def test_closure_removes_active_owned_records_and_preserves_other_account(self):
        from app.backend.models import Star
        self.db.add(Star(user_id=self.other.id,version_id=self.version.id));self.db.commit()
        user_id=self.owner.id;session_id=self.session.id;version_id=self.version.id;other_id=self.other.id
        response=await self.close_account();self.assertEqual(response.status_code,200)
        self.db.expire_all()
        self.assertIsNone(self.db.get(User,user_id));self.assertIsNone(self.db.get(ChatSession,session_id));self.assertIsNone(self.db.get(GameVersion,version_id))
        self.assertEqual(self.db.query(ChatMessage).filter_by(session_id=session_id).count(),0)
        self.assertIsNotNone(self.db.get(User,other_id));self.assertTrue(self.foreign_file.exists());self.assertFalse(self.file.exists())
        self.db.refresh(self.foreign_version);self.assertIsNone(self.foreign_version.parent_version_id)
        self.assertEqual((await self.client.get('/api/auth/me',headers=self.owner_headers)).status_code,401)
        self.assertEqual((await self.client.get('/api/auth/me',headers=self.other_headers)).status_code,200)

    async def test_failed_database_commit_restores_rows_files_and_deletion_evidence(self):
        from app.backend.recovery import read_deleted_accounts
        with patch('app.backend.accounts._commit_deletion',side_effect=RuntimeError('synthetic database failure')):
            response=await self.close_account()
        self.assertEqual(response.status_code,503);self.assertTrue(self.file.exists());self.db.expire_all()
        self.assertIsNotNone(self.db.get(User,self.owner.id));self.assertIsNotNone(self.db.get(GameVersion,self.version.id))
        self.assertNotIn(self.owner.id,read_deleted_accounts(os.environ['DATA_DIR']))
        self.assertEqual((await self.client.get('/api/auth/me',headers=self.owner_headers)).status_code,200)

    async def test_failed_game_move_preserves_account_and_files(self):
        import app.backend.accounts as accounts
        original=accounts.os.replace
        def refuse_game_move(source,destination):
            if Path(source).parent==Path(os.environ['VERSIONS_DIR']):raise OSError('synthetic file failure')
            return original(source,destination)
        with patch('app.backend.accounts.os.replace',side_effect=refuse_game_move):
            response=await self.close_account()
        self.assertEqual(response.status_code,503);self.assertTrue(self.file.exists());self.db.expire_all()
        self.assertIsNotNone(self.db.get(User,self.owner.id))

    async def test_surviving_deletion_evidence_is_mandatory_and_applies_to_an_older_restore(self):
        import sqlite3
        from app.backend.recovery import snapshot,restore,read_deleted_accounts
        from app.backend.agent import get_base_game_path
        saved=snapshot(os.environ['DATA_DIR'],os.environ['VERSIONS_DIR'],get_base_game_path())
        user_id=self.owner.id;other_id=self.other.id
        response=await self.close_account();self.assertEqual(response.status_code,200)
        destination=Path(_TEST_ROOT.name)/('closed-restore-'+secrets.token_hex(6))
        with self.assertRaisesRegex(RuntimeError,'deletion evidence'):
            restore(saved,destination)
        self.assertFalse(destination.exists())
        restore(saved,destination,deletions=read_deleted_accounts(os.environ['DATA_DIR']))
        from contextlib import closing
        with closing(sqlite3.connect(destination/'openworld.db')) as database:
            self.assertEqual(database.execute('SELECT count(*) FROM users WHERE id=?',(user_id,)).fetchone()[0],0)
            self.assertEqual(database.execute('SELECT count(*) FROM users WHERE id=?',(other_id,)).fetchone()[0],1)
            self.assertEqual(database.execute('SELECT count(*) FROM chat_sessions WHERE user_id=?',(user_id,)).fetchone()[0],0)
        self.assertFalse((destination/'versions'/self.file.name).exists());self.assertTrue((destination/'versions'/self.foreign_file.name).exists())

    async def test_startup_reconciles_a_crash_after_durable_closure_intent(self):
        from app.backend.recovery import read_deleted_accounts,write_deleted_accounts,reconcile_deleted_accounts
        user_id=self.owner.id;other_id=self.other.id
        previous=read_deleted_accounts(os.environ['DATA_DIR'],create=True)
        write_deleted_accounts(os.environ['DATA_DIR'],previous|{user_id})
        reconcile_deleted_accounts(os.environ['DATA_DIR'],os.environ['VERSIONS_DIR'])
        self.db.expire_all();self.assertIsNone(self.db.get(User,user_id));self.assertIsNotNone(self.db.get(User,other_id))
        self.assertFalse(self.file.exists());self.assertTrue(self.foreign_file.exists())


    async def test_account_action_limit_does_not_block_another_account(self):
        from app.backend.accounts import account_action
        from fastapi import HTTPException
        for _ in range(8):account_action(self.owner.id)
        with self.assertRaises(HTTPException) as raised:account_action(self.owner.id)
        self.assertEqual(raised.exception.status_code,429)
        account_action(self.other.id)





class AdminReviews(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await PrivateAccess.asyncSetUp(self)
        self.admin=User(email=secrets.token_hex(5)+'@admin.invalid',username='admin'+secrets.token_hex(5),password_hash='unused',is_admin=True)
        self.db.add(self.admin);self.db.commit()
        self.admin_headers={'Authorization':'Bearer '+create_access_token(self.admin.id)}
        from app.backend.request_limits import _buckets
        _buckets.clear()

    async def asyncTearDown(self):await PrivateAccess.asyncTearDown(self)

    async def test_review_requires_admin_and_explicit_owner_submission(self):
        for headers in [{},self.owner_headers]:
            self.assertIn((await self.client.get('/api/admin/preview/'+self.version.id,headers=headers)).status_code,[401,403])
        self.assertEqual((await self.client.get('/api/admin/preview/'+self.version.id,headers=self.admin_headers)).status_code,404)
        for action in ['approve','decline']:
            self.assertEqual((await self.client.post('/api/admin/'+action+'/'+self.version.id,headers=self.admin_headers)).status_code,400)
        self.version.is_suggested=True;self.version.suggestion_status='pending';self.db.commit()
        response=await self.client.get('/api/admin/preview/'+self.version.id,headers=self.admin_headers)
        self.assertEqual(response.status_code,200);self.assertIn('PRIVATE_SYNTHETIC_GAME',response.text)
        self.assertIn('sandbox allow-scripts allow-pointer-lock',response.headers['content-security-policy'])
        self.assertEqual((await self.client.get('/game/version/'+self.version.id,headers=self.admin_headers)).status_code,404)

    async def test_approval_commit_failure_restores_the_previous_base_game(self):
        from app.backend.agent import get_base_game_path
        self.version.is_suggested=True;self.version.suggestion_status='pending';self.db.commit()
        base=Path(get_base_game_path());previous=base.read_bytes()
        with patch('sqlalchemy.orm.Session.commit',side_effect=RuntimeError('synthetic review failure')):
            response=await self.client.post('/api/admin/approve/'+self.version.id,headers=self.admin_headers)
        self.assertEqual(response.status_code,503);self.assertEqual(base.read_bytes(),previous)
        self.db.expire_all();self.assertEqual(self.db.get(GameVersion,self.version.id).suggestion_status,'pending')

    async def test_completed_review_is_idempotent_and_cannot_reverse_another_decision(self):
        from app.backend.agent import get_base_game_path
        self.version.is_suggested=True;self.version.suggestion_status='pending';self.db.commit()
        self.assertEqual((await self.client.post('/api/admin/approve/'+self.version.id,headers=self.admin_headers)).status_code,200)
        base=Path(get_base_game_path());base.write_text('Later independent base game')
        self.assertEqual((await self.client.post('/api/admin/approve/'+self.version.id,headers=self.admin_headers)).status_code,200)
        self.assertEqual(base.read_text(),'Later independent base game')
        self.assertEqual((await self.client.post('/api/admin/decline/'+self.version.id,headers=self.admin_headers)).status_code,409)
        # Keep the synthetic recovery fixture's base as a valid game for later cases.
        base.write_text('<!doctype html><html><body>Recovered synthetic base</body></html>')


class PublicBaseTransport(unittest.IsolatedAsyncioTestCase):
    async def test_public_base_keeps_opaque_policy_and_missing_file_offers_retry(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test.invalid') as client:
            response=await client.get('/game/base')
            self.assertEqual(response.status_code,200)
            self.assertIn('sandbox allow-scripts allow-pointer-lock',response.headers['content-security-policy'])
            self.assertNotIn('allow-same-origin',response.headers['content-security-policy'])
            self.assertNotIn('ow_token',response.text)
            missing=Path(_TEST_ROOT.name)/'missing-public-base.html'
            with patch('app.backend.main.get_base_game_path',return_value=str(missing)):
                failed=await client.get('/game/base')
            self.assertEqual(failed.status_code,404)
            self.assertIn('Try loading the game again',failed.text)
            self.assertIn('sandbox allow-scripts allow-pointer-lock',failed.headers['content-security-policy'])
            self.assertEqual(failed.headers['cache-control'],'no-store')


if __name__=='__main__':unittest.main(verbosity=2)
