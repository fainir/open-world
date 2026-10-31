"""Synthetic local beta acceptance. No live gateway/model/account request."""
import asyncio,base64,hashlib,json,os,secrets,subprocess,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import test_security
import httpx
from app.backend.database import init_db,SessionLocal
from app.backend.models import IncludedCreation,ChatSession,GameVersion
from app.backend.main import app
from app.backend import included_ai as beta
from app.backend.request_limits import _buckets

class IncludedBeta(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        init_db();_buckets.clear();self.db=SessionLocal();self.db.query(IncludedCreation).delete();self.db.commit()
        self.guest=secrets.token_urlsafe(32);self.headers={'X-OpenWorld-Guest':self.guest}
        session=ChatSession(guest_access_hash=hashlib.sha256(self.guest.encode()).hexdigest());self.db.add(session);self.db.flush()
        filename=uuid.uuid4().hex+'.html';Path(os.environ['VERSIONS_DIR'],filename).write_text('<!doctype html><html><body>OLD_BETA_MARKER</body></html>')
        version=GameVersion(session_id=session.id,version_number=0,description='Synthetic beta base',file_path=filename);self.db.add(version);self.db.commit()
        self.payload={'message':'Add a small blue building','session_id':session.id,'current_version_id':version.id,'funding':'included','request_id':str(uuid.uuid4())}
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test.invalid')
    async def asyncTearDown(self):await self.client.aclose();self.db.close()
    def answer(self,reason='end_turn'):
        return SimpleNamespace(stop_reason=reason,content=[SimpleNamespace(type='text',text='<<<SEARCH\nOLD_BETA_MARKER\n===\nNEW_BETA_MARKER\n>>>SEARCH\n<description>A small blue building appeared.</description><suggestions>[]</suggestions>')])
    async def post(self,payload=None,headers=None):return await self.client.post('/api/chat',json=payload or self.payload,headers=headers or self.headers)
    async def test_default_off_never_calls_or_consumes(self):
        with patch.object(beta,'generate') as provider,patch('app.backend.agent.anthropic.Anthropic') as direct:
            self.assertFalse((await self.client.get('/api/creation-allowance',headers=self.headers)).json()['enabled'])
            result=await self.post();self.assertEqual(result.status_code,503);self.assertEqual(result.json()['dispatched'],False);provider.assert_not_called();direct.assert_not_called()
        self.assertEqual(self.db.query(IncludedCreation).count(),0)
    async def test_guest_success_real_patch_and_replay_without_charge(self):
        with patch.object(beta,'ready',return_value=True),patch.object(beta,'generate',return_value=self.answer()) as provider,patch('app.backend.agent.anthropic.Anthropic') as direct:
            first=await self.post();self.assertEqual(first.status_code,200,first.text);again=await self.post();self.assertEqual(again.status_code,200);self.assertEqual(first.json()['version_id'],again.json()['version_id']);self.assertEqual(provider.call_count,1);direct.assert_not_called()
        version=self.db.get(GameVersion,first.json()['version_id']);self.assertIn('NEW_BETA_MARKER',Path(os.environ['VERSIONS_DIR'],version.file_path).read_text());self.assertEqual(first.json()['included_remaining'],1)
        self.assertEqual(len(provider.call_args.args),2);self.assertNotIn(self.guest,json.dumps(provider.call_args.args));self.assertNotIn('api_key',provider.call_args.kwargs)
    async def test_actor_daily_limit_is_persistent(self):
        with patch.object(beta,'ready',return_value=True),patch.object(beta,'generate',return_value=self.answer()) as provider:
            for _ in range(2):
                response=await self.post({**self.payload,'request_id':str(uuid.uuid4())});self.assertEqual(response.status_code,200,response.text)
            self.db.close();self.db=SessionLocal()
            response=await self.post({**self.payload,'request_id':str(uuid.uuid4())});self.assertEqual(response.status_code,429);self.assertEqual(response.json()['code'],'daily_limit');self.assertEqual(provider.call_count,2)
    async def test_ip_limit_survives_new_guest_ids(self):
        with patch.object(beta,'ready',return_value=True),patch.object(beta,'generate',return_value=SimpleNamespace(stop_reason='end_turn',content=[SimpleNamespace(type='text',text='Synthetic counted response')])) as provider:
            for i in range(5):
                body={'message':'A small blue building','funding':'included','request_id':str(uuid.uuid4())}
                response=await self.post(body,{'X-OpenWorld-Guest':secrets.token_urlsafe(32)})
                self.assertEqual(response.status_code,200 if i<4 else 429,response.text)
            self.assertEqual(provider.call_count,4)
    async def test_unknown_outcome_held_and_never_falls_back(self):
        with patch.object(beta,'ready',return_value=True),patch.object(beta,'generate',side_effect=beta.IncludedError('uncertain','Result unknown')) as provider,patch('app.backend.agent.anthropic.Anthropic') as direct:
            self.assertEqual((await self.post()).status_code,503);self.assertEqual((await self.post()).status_code,409);self.assertEqual(provider.call_count,1);direct.assert_not_called()
        self.db.expire_all();self.assertEqual(self.db.get(IncludedCreation,self.payload['request_id']).status,'unknown')
    async def test_pre_dispatch_refusal_does_not_consume(self):
        with patch.object(beta,'ready',return_value=True),patch.object(beta,'generate',side_effect=beta.IncludedError('budget','Shared beta budget unavailable',dispatched=False)) as provider:
            response=await self.post();self.assertEqual(response.status_code,503);self.assertEqual(response.json()['included_remaining'],2)
            self.assertEqual((await self.post()).status_code,409);self.assertEqual(provider.call_count,1)
    async def test_context_boundary_and_refusal_do_not_save_game(self):
        with self.assertRaises(beta.IncludedError) as error:beta.generate('x'*(beta.MAX_CONTEXT_BYTES+1),[{'role':'user','content':'small edit'}],request_id=str(uuid.uuid4()),actor='a'*64,network='b'*64)
        self.assertEqual(error.exception.code,'context_limit');self.assertFalse(error.exception.dispatched)
        before=self.db.query(GameVersion).count()
        with patch.object(beta,'ready',return_value=True),patch.object(beta,'generate',return_value=self.answer('max_tokens')):
            response=await self.post();self.assertEqual(response.status_code,400)
        self.assertEqual(self.db.query(GameVersion).count(),before)
    async def test_uuid_payload_binding_and_missing_guest(self):
        with patch.object(beta,'ready',return_value=True),patch.object(beta,'generate',return_value=self.answer()) as provider:
            self.assertEqual((await self.post()).status_code,200)
            response=await self.post({**self.payload,'message':'Different payload'});self.assertEqual(response.status_code,409);self.assertEqual(response.json()['code'],'request_conflict');self.assertEqual(provider.call_count,1)
            response=await self.client.post('/api/chat',json={**self.payload,'session_id':None,'current_version_id':None,'request_id':str(uuid.uuid4())});self.assertEqual(response.status_code,400)
    async def test_client_cancellation_cannot_retry_an_already_started_call(self):
        import threading
        started=threading.Event();release=threading.Event()
        def generate(*args,**kwargs):started.set();release.wait(5);return self.answer()
        with patch.object(beta,'ready',return_value=True),patch.object(beta,'generate',side_effect=generate) as provider:
            request=asyncio.create_task(self.post())
            while not started.is_set():await asyncio.sleep(.01)
            request.cancel();release.set()
            try:await request
            except asyncio.CancelledError:pass
            for _ in range(100):
                self.db.expire_all();record=self.db.get(IncludedCreation,self.payload['request_id'])
                if record.status=='complete':break
                await asyncio.sleep(.01)
            self.assertEqual(record.status,'complete')
            replay=await self.post();self.assertEqual(replay.status_code,200);self.assertEqual(provider.call_count,1)

    async def test_closed_session_is_not_recreated_after_included_call(self):
        def generate(*args,**kwargs):
            with SessionLocal() as db:
                db.query(ChatSession).filter_by(id=self.payload['session_id']).delete();db.commit()
            return self.answer()
        before=self.db.query(GameVersion).count()
        with patch.object(beta,'ready',return_value=True),patch.object(beta,'generate',side_effect=generate):
            response=await self.post();self.assertEqual(response.status_code,400);self.assertIn('session was closed',response.text)
        self.assertEqual(self.db.query(GameVersion).count(),before)

    async def test_byok_still_uses_original_sdk_and_budget(self):
        body={**self.payload,'funding':'byok','api_key':'synthetic-own-provider-key'}
        with patch.object(beta,'generate') as included,patch('app.backend.agent.anthropic.Anthropic') as direct:
            direct.return_value.messages.create.return_value=self.answer();response=await self.post(body);self.assertEqual(response.status_code,200);included.assert_not_called();self.assertEqual(direct.call_args.kwargs['api_key'],body['api_key']);self.assertEqual(direct.return_value.messages.create.call_args.kwargs['max_tokens'],16000)
        self.assertEqual(self.db.query(IncludedCreation).count(),0)

class SigningAndQuota(unittest.TestCase):
    def test_cross_language_signature_contract(self):
        from app.backend.portfolio_signing import public_key,sign
        body=b'{"version":1,"app":"openworld","request_id":"synthetic"}';timestamp=12345
        with patch.dict(os.environ,{'JWT_SECRET':'a'*64}):key=public_key();signature=sign(body,'synthetic',timestamp)
        script="""const c=require('crypto'),[pub,sig,body]=process.argv.slice(1);const message=['portfolio-claude/v1','POST','/api/claude/v1/complete','openworld','generate','synthetic','12345',c.createHash('sha256').update(Buffer.from(body,'base64')).digest('hex')].join('\\n');const seed=c.hkdfSync('sha256',Buffer.from('a'.repeat(64)),Buffer.alloc(0),Buffer.from('portfolio-claude/v1/openworld'),32);const priv=c.createPrivateKey({key:Buffer.concat([Buffer.from('302e020100300506032b657004220420','hex'),Buffer.from(seed)]),format:'der',type:'pkcs8'});if(c.createPublicKey(priv).export({format:'der',type:'spki'}).toString('base64url')!==pub||!c.verify(null,Buffer.from(message),c.createPublicKey({key:Buffer.from(pub,'base64url'),format:'der',type:'spki'}),Buffer.from(sig,'base64url')))process.exit(1);"""
        subprocess.run(['node','-e',script,key,signature,base64.b64encode(body).decode()],check=True,capture_output=True)
    def test_no_dispatch_refunds_actor_but_bounds_network_storage(self):
        init_db()
        with SessionLocal() as db:
            db.query(IncludedCreation).delete();db.commit()
            for i in range(4):
                db.add(IncludedCreation(id=str(uuid.uuid4()),actor='refused-actor',network='refused-network',payload_hash=str(i),status='rejected'));db.commit()
                self.assertEqual(beta.allowance(db,'refused-actor','refused-network'),min(2,3-i))

    def test_atomic_daily_reservations(self):
        from concurrent.futures import ThreadPoolExecutor
        init_db()
        with SessionLocal() as db:db.query(IncludedCreation).delete();db.commit()
        def reserve(i):
            with SessionLocal() as db:
                try:beta.reserve(db,str(uuid.uuid4()),'synthetic-concurrent-actor','synthetic-network',{'index':i});return True
                except beta.IncludedError:return False
        with ThreadPoolExecutor(max_workers=4) as pool:self.assertEqual(sum(pool.map(reserve,range(4))),2)

class GatewayTransport(unittest.TestCase):
    def test_strict_signed_fixed_gateway_and_response(self):
        request_id=str(uuid.uuid4());captured=[]
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):return json.dumps({'ok':True,'request_id':request_id,'model':beta.MODEL,'content':[{'type':'text','text':'Synthetic text'}],'stop_reason':'end_turn','usage':{'input_tokens':1,'output_tokens':1}}).encode()
        class Opener:
            def open(self,request,timeout):captured.append((request,timeout));return Response()
        with patch.dict(os.environ,{'OPENWORLD_INCLUDED_AI_ENABLED':'1','JWT_SECRET':'a'*64}),patch.object(beta,'build_opener',return_value=Opener()) as opener:
            result=beta.generate('Synthetic system',[{'role':'user','content':'Synthetic request'}],request_id=request_id,actor='a'*64,network='b'*64)
        request,timeout=captured[0];body=json.loads(request.data);self.assertEqual(request.full_url,beta.GATEWAY);self.assertEqual(timeout,110)
        self.assertEqual(set(body),{'version','app','feature','request_id','actor','actor_ip','input'});self.assertEqual(body['input']['messages'][0]['content'],'Synthetic request');self.assertNotIn('model',body);self.assertEqual(result.content[0].text,'Synthetic text')
        self.assertIsNone(opener.call_args.args[0].redirect_request(None,None,None,None,None,None))
        self.assertTrue(request.get_header('X-portfolio-signature'));self.assertTrue(request.get_header('X-portfolio-timestamp'))
    def test_typed_dispatch_proof_and_timeout_hold(self):
        from urllib.error import HTTPError
        import io
        class Opener:
            def __init__(self,error):self.error=error
            def open(self,*args,**kwargs):raise self.error
        for code,dispatched,expected in [('budget_paused',False,False),('budget_paused',None,None),('outcome_unknown',False,None)]:
            error=HTTPError(beta.GATEWAY,503,'unavailable',{},io.BytesIO(json.dumps({'ok':False,'dispatched':dispatched,'error':{'code':code,'message':'PRIVATE_GATEWAY_TEXT'}}).encode()))
            with patch.dict(os.environ,{'OPENWORLD_INCLUDED_AI_ENABLED':'1','JWT_SECRET':'a'*64}),patch.object(beta,'build_opener',return_value=Opener(error)):
                with self.assertRaises(beta.IncludedError) as caught:beta.generate('system',[{'role':'user','content':'request'}],request_id=str(uuid.uuid4()),actor='a'*64,network='b'*64)
            self.assertIs(caught.exception.dispatched,expected);self.assertNotIn('PRIVATE_GATEWAY_TEXT',str(caught.exception))
        with patch.dict(os.environ,{'OPENWORLD_INCLUDED_AI_ENABLED':'1','JWT_SECRET':'a'*64}),patch.object(beta,'build_opener',return_value=Opener(TimeoutError())):
            with self.assertRaises(beta.IncludedError) as caught:beta.generate('system',[{'role':'user','content':'request'}],request_id=str(uuid.uuid4()),actor='a'*64,network='b'*64)
        self.assertIsNone(caught.exception.dispatched);self.assertEqual(caught.exception.code,'outcome_unknown')
