"""First AI edit: one-click ideas over the game. Synthetic ASGI only; no provider request."""
import hashlib,json,os,re,secrets,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import test_security  # installs the existing disposable SQLite environment first
from test_security import _Document
import httpx
from app.backend.database import init_db,SessionLocal
from app.backend.models import IncludedCreation,ChatSession,GameVersion
from app.backend.main import app
from app.backend import included_ai as beta
from app.backend.request_limits import _buckets

DASHES=['–','—','&ndash;','&mdash;','&#8211;','&#8212;','&#x2013;','&#x2014;']


def card_text(html):
    """User-visible text of the ideas card, including the strings its script writes."""
    card=html.split('<section id="ow-ideas"',1)[1].split('</section>',1)[0]
    script=html.split('// ── First AI edit:',1)[1].split('refreshAllowance();',1)[0]
    return card+'\n'+'\n'.join(re.findall(r"'([^'\n]*)'",script))


class IdeasCard(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        init_db();_buckets.clear()
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://open-world.gg')
    async def asyncTearDown(self):await self.client.aclose()

    async def test_home_and_private_version_shell_carry_the_hidden_ideas_card(self):
        for path in ['/','/v/'+str(uuid.uuid4())]:
            r=await self.client.get(path);self.assertEqual(r.status_code,200)
            doc=_Document(r.text);ids={a.get('id'):a for t,a in doc.tags if a.get('id')}
            # Hidden until the allowance check says included edits are available.
            self.assertIn('hidden',ids['ow-ideas']);self.assertEqual(ids['ow-ideas'].get('aria-labelledby'),'ow-ideas-title')
            for name in ['ow-ideas-card','ow-ideas-hide','ow-ideas-list','ow-ideas-progress','ow-ideas-stage','ow-ideas-share','ow-ideas-more','ow-ideas-left','ow-ideas-pill','ow-examples']:
                self.assertIn(name,ids,name)
            self.assertEqual(ids['ow-ideas-stage'].get('aria-live'),'polite')
            for button in ['ow-ideas-hide','ow-ideas-share','ow-ideas-more','ow-ideas-pill']:self.assertEqual(ids[button].get('type'),'button',button)
            # The card sits after the editor panel so the desktop rule can keep it over the game.
            self.assertLess(r.text.index('id="ow-panel"'),r.text.index('id="ow-ideas"'))

    async def test_three_one_click_ideas_say_plainly_how_many_free_edits_remain(self):
        html=(await self.client.get('/')).text
        ideas=re.findall(r"\{label:'([^']+)',prompt:'([^']+)'\}",html)
        self.assertEqual([json.loads('"'+label+'"').split(' ',1)[1] for label,_ in ideas],['Make it snow','Turn the sky purple','Add a dragon'])
        for _,prompt in ideas:self.assertTrue(0<len(prompt)<=8000)
        for text in ["' free AI edits left'","'1 free AI edit left'",'No free AI edits left right now','Each try counts, even if it fails, and comes back 24 hours after you use it.',
                     'Write your own','Claude is editing your game','Your version is ready','Share your version','Only you can see it.','That edit did not finish']:
            self.assertIn(text,html)
        # Ideas reuse the normal send path, which enforces the included allowance and checks.
        self.assertIn("input.value=idea.prompt;editSource='idea';sendMessage();",html)
        self.assertIn("fetch(source==='idea'?'/api/chat/idea':'/api/chat'",html)
        self.assertIn('writeStore(sessionStorage,SHARE_PROMPT,data.version_id)',html)

    async def test_new_card_copy_has_no_en_or_em_dashes(self):
        text=card_text((await self.client.get('/')).text)
        self.assertIn('Change this game with words',text)
        for dash in DASHES:self.assertNotIn(dash,text)


class IdeaEditPath(unittest.IsolatedAsyncioTestCase):
    """/api/chat/idea is the same handler as /api/chat, only a separate path for request logs."""
    async def asyncSetUp(self):
        init_db();_buckets.clear();self.db=SessionLocal();self.db.query(IncludedCreation).delete();self.db.commit()
        self.guest=secrets.token_urlsafe(32);self.headers={'X-OpenWorld-Guest':self.guest}
        session=ChatSession(guest_access_hash=hashlib.sha256(self.guest.encode()).hexdigest());self.db.add(session);self.db.flush()
        filename=uuid.uuid4().hex+'.html';Path(os.environ['VERSIONS_DIR'],filename).write_text('<!doctype html><html><body>IDEA_OLD_MARKER</body></html>')
        version=GameVersion(session_id=session.id,version_number=0,description='Synthetic idea base',file_path=filename);self.db.add(version);self.db.commit()
        self.payload={'message':'Make it snow: add gently falling white snowflakes.','session_id':session.id,'current_version_id':version.id,'funding':'included','request_id':str(uuid.uuid4())}
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test.invalid')
    async def asyncTearDown(self):await self.client.aclose();self.db.close()
    def answer(self):
        return SimpleNamespace(stop_reason='end_turn',content=[SimpleNamespace(type='text',text='<<<SEARCH\nIDEA_OLD_MARKER\n===\nIDEA_SNOW_MARKER\n>>>SEARCH\n<description>Snow falls.</description><suggestions>[]</suggestions>')])

    async def test_default_off_idea_path_matches_chat_and_never_consumes(self):
        with patch.object(beta,'generate') as provider,patch('app.backend.agent.anthropic.Anthropic') as direct:
            plain=await self.client.post('/api/chat',json=self.payload,headers=self.headers)
            idea=await self.client.post('/api/chat/idea',json={**self.payload,'request_id':str(uuid.uuid4())},headers=self.headers)
            provider.assert_not_called();direct.assert_not_called()
        self.assertEqual((plain.status_code,plain.json()['code'],plain.json()['dispatched']),(503,'unavailable',False))
        self.assertEqual((idea.status_code,idea.json()['code'],idea.json()['dispatched']),(503,'unavailable',False))
        self.assertEqual(self.db.query(IncludedCreation).count(),0)

    async def test_idea_edit_uses_the_same_allowance_and_replay_as_typed_edits(self):
        with patch.object(beta,'ready',return_value=True),patch.object(beta,'generate',return_value=self.answer()) as provider,patch('app.backend.agent.anthropic.Anthropic') as direct:
            first=await self.client.post('/api/chat/idea',json=self.payload,headers=self.headers);self.assertEqual(first.status_code,200,first.text)
            # The same creation reference through the typed path replays; it is never sent or counted twice.
            again=await self.client.post('/api/chat',json=self.payload,headers=self.headers);self.assertEqual(again.status_code,200,again.text)
            self.assertEqual(first.json()['version_id'],again.json()['version_id']);self.assertEqual(provider.call_count,1);direct.assert_not_called()
            allowance=(await self.client.get('/api/creation-allowance',headers=self.headers)).json()
        self.assertEqual(first.json()['included_remaining'],1);self.assertEqual(allowance['remaining'],1)
        version=self.db.get(GameVersion,first.json()['version_id']);self.assertFalse(version.is_shared)
        self.assertIn('IDEA_SNOW_MARKER',Path(os.environ['VERSIONS_DIR'],version.file_path).read_text())

    async def test_idea_and_typed_edits_share_one_generation_rate_bucket(self):
        body={'message':'x','api_key':'synthetic-key-never-used'}
        with patch('app.backend.agent.anthropic.Anthropic') as direct:
            for index in range(10):
                r=await self.client.post('/api/chat/idea' if index%2 else '/api/chat',json={**body,'session_id':'missing-'+str(index)})
                self.assertNotEqual(r.status_code,429,index)
            for path in ['/api/chat','/api/chat/idea']:
                r=await self.client.post(path,json=body);self.assertEqual(r.status_code,429,path)
            direct.assert_not_called()


if __name__=='__main__':unittest.main(verbosity=2)
