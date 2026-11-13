"""Share loop on shared game pages: Made with, Remix this and one-tap share. Synthetic ASGI only; no provider request."""
import os,re,secrets,unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
import test_security  # installs the existing disposable SQLite environment first
from test_security import _Document
import httpx
from app.backend.database import init_db,SessionLocal
from app.backend.models import User,ChatSession,GameVersion
from app.backend.auth import create_access_token
from app.backend.game_security import GAME_CSP
from app.backend.main import DEMO_OWNER_EMAIL, DEMO_OWNER_NAME, app
from app.backend.request_limits import _buckets

DASHES=['–','—','&ndash;','&mdash;','&#8211;','&#8212;','&#x2013;','&#x2014;']


class _Text(HTMLParser):
    """Visible text of a page (no script or style bodies)."""
    def __init__(self,html):
        super().__init__();self.parts=[];self.skip=0;self.feed(html)
    def handle_starttag(self,tag,attrs):self.skip+=tag in('script','style')
    def handle_endtag(self,tag):self.skip-=tag in('script','style')
    def handle_data(self,data):
        if not self.skip and data.strip():self.parts.append(' '.join(data.split()))


class ShareLoop(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        init_db();_buckets.clear();self.db=SessionLocal();suffix=secrets.token_hex(5)
        self.owner=User(email=suffix+'@owner.invalid',username='owner'+suffix,password_hash='unused');self.db.add(self.owner);self.db.flush()
        self.session=ChatSession(user_id=self.owner.id);self.db.add(self.session);self.db.flush()
        self.file=Path(os.environ['VERSIONS_DIR'])/(suffix+'.html')
        self.file.write_text('<!doctype html><html><body>SHARED_SYNTHETIC_GAME_'+suffix+'</body></html>')
        self.version=GameVersion(session_id=self.session.id,user_id=self.owner.id,version_number=3,description='Purple sky city',
                                 publish_title='Purple City',file_path=self.file.name,is_shared=True,share_slug=secrets.token_hex(16))
        self.db.add(self.version);self.db.commit();self.slug=self.version.share_slug;self.marker='SHARED_SYNTHETIC_GAME_'+suffix
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://open-world.gg')
    async def asyncTearDown(self):
        await self.client.aclose();self.db.close()

    async def test_shared_page_has_made_with_link_remix_and_one_tap_share(self):
        r=await self.client.get('/shared/'+self.slug);self.assertEqual(r.status_code,200)
        doc=_Document(r.text);ids={a.get('id'):(t,a) for t,a in doc.tags if a.get('id')}
        made=[a for t,a in doc.tags if t=='a' and a.get('class')=='ow-made']
        self.assertEqual([a['href'] for a in made],['/'])
        text=_Text(r.text).parts
        self.assertIn('Made with',text);self.assertIn('- make your own',text);self.assertIn('OpenWorld',text)
        self.assertIn('Made with OpenWorld - make your own',re.sub(r'<[^>]+>','',r.text))
        self.assertEqual(ids['ow-remix'],('a',{'class':'ow-btn ow-remix','id':'ow-remix','href':'/remix/'+self.slug}))
        self.assertEqual(ids['ow-share'][1].get('type'),'button')
        self.assertIn('hidden',ids['ow-copy'][1]);self.assertEqual(ids['ow-status'][1].get('aria-live'),'polite')
        self.assertEqual(ids['ow-game'][1]['src'],'/game/shared/'+self.slug)
        for path in ['/static/js/share-link.js','/static/js/shared.js']:
            self.assertIn('<script src="'+path+'" defer></script>',r.text)
            self.assertEqual((await self.client.get(path)).status_code,200)
        for dash in DASHES:self.assertNotIn(dash,' '.join(text))
        self.assertNotIn(self.version.id,r.text);self.assertNotIn(self.marker,r.text)

    async def test_remix_opens_the_editor_on_that_shared_version(self):
        r=await self.client.get('/remix/'+self.slug,follow_redirects=False)
        self.assertEqual(r.status_code,302);self.assertEqual(r.headers['location'],'/v/'+self.version.id+'?remix=1')
        # The studio shell for that version is the normal editor and loads the shared game for anyone.
        self.assertEqual((await self.client.get('/v/'+self.version.id+'?remix=1')).status_code,200)
        game=await self.client.get('/game/version/'+self.version.id);self.assertEqual(game.status_code,200);self.assertIn(self.marker,game.text)

    async def test_only_published_first_party_games_use_the_demo_startup(self):
        original = '<!-- THEME: Test demo -->\n' + Path('index.html').read_text(encoding='utf-8')
        self.file.write_text(original, encoding='utf-8')
        paths = ('/game/shared/' + self.slug, '/game/version/' + self.version.id)
        email, username, title = self.owner.email, self.owner.username, self.version.publish_title
        self.version.publish_title = 'Enchanted Forest'
        try:
            for owner_email, owner_name, published, expected in (
                (email, username, True, False),
                (email, DEMO_OWNER_NAME, True, False),
                (DEMO_OWNER_EMAIL, DEMO_OWNER_NAME, False, False),
                (DEMO_OWNER_EMAIL, DEMO_OWNER_NAME, True, True),
            ):
                self.owner.email, self.owner.username = owner_email, owner_name
                self.version.is_published = published
                self.db.commit()
                for path in paths:
                    with self.subTest(path=path, published=published, startup=expected):
                        response = await self.client.get(path)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.headers['Content-Security-Policy'], GAME_CSP)
                        self.assertEqual(response.headers['Cache-Control'], 'private, no-store')
                        self.assertEqual('ow-base-ready' in response.text, expected)
                        self.assertEqual('Click or press anything to start' in response.text, not expected)
                entry = await self.client.get('/play/from-portfolio?next=https://example.com/')
                self.assertEqual(entry.status_code, 302)
                self.assertEqual(entry.headers['location'], '/shared/' + self.slug if expected else '/')
                self.assertEqual(entry.headers['cache-control'], 'no-store')
                self.assertEqual(self.file.read_text(encoding='utf-8'), original)
        finally:
            self.owner.email, self.owner.username = email, username
            self.version.publish_title = title
            self.version.is_published = False
            self.file.write_text('<!doctype html><html><body>' + self.marker + '</body></html>', encoding='utf-8')
            self.db.commit()

    async def test_remix_of_private_or_missing_games_reveals_nothing(self):
        private=GameVersion(session_id=self.session.id,user_id=self.owner.id,version_number=4,description='PRIVATE_SYNTHETIC',
                            file_path=self.file.name,is_shared=False,share_slug=secrets.token_hex(16))
        gone=GameVersion(session_id=self.session.id,user_id=self.owner.id,version_number=5,description='PRIVATE_SYNTHETIC',
                         file_path='missing-'+secrets.token_hex(5)+'.html',is_shared=True,share_slug=secrets.token_hex(16))
        self.db.add_all([private,gone]);self.db.commit()
        try:
            for slug in [private.share_slug,gone.share_slug,secrets.token_hex(16),'%22%3E%3Cscript%3E']:
                with self.subTest(slug=slug):
                    r=await self.client.get('/remix/'+slug,follow_redirects=False)
                    self.assertEqual(r.status_code,404);self.assertNotIn('location',r.headers)
                    for leaked in [private.id,gone.id,'PRIVATE_SYNTHETIC','<script']:self.assertNotIn(leaked,r.text)
        finally:
            # Later recovery cases require every referenced game file to exist.
            self.db.delete(private);self.db.delete(gone);self.db.commit()

    async def test_first_remix_edit_branches_a_private_copy_of_the_shared_game(self):
        guest={'X-OpenWorld-Guest':secrets.token_urlsafe(32)}
        seen={}
        def fake_agent(api_key,message,session,db,current_path,parent_version_id,image,provider):
            seen.update(path=current_path,parent=parent_version_id,session=session.id)
            return {'message':'Synthetic reply without a change'}
        with patch('app.backend.main.run_agent',side_effect=fake_agent):
            r=await self.client.post('/api/chat',headers=guest,json={'message':'Make it snow','current_version_id':self.version.id,
                                                                      'api_key':'synthetic-key-never-used','funding':'byok'})
        self.assertEqual(r.status_code,200,r.text);new_session=r.json()['session_id']
        self.assertNotEqual(new_session,self.session.id);self.assertEqual(seen['session'],new_session)
        self.assertEqual(seen['parent'],self.version.id);self.assertEqual(Path(seen['path']),self.file)
        self.db.expire_all()
        copy=self.db.query(GameVersion).filter(GameVersion.session_id==new_session,GameVersion.version_number==0).one()
        self.assertFalse(copy.is_shared);self.assertNotEqual(copy.file_path,self.file.name)
        self.assertEqual((Path(os.environ['VERSIONS_DIR'])/copy.file_path).read_text(),self.file.read_text())
        # The remixer cannot read or change the original owner's private chat or versions.
        self.assertEqual((await self.client.get('/api/versions/'+self.session.id,headers=guest)).status_code,404)
        self.assertEqual((await self.client.post('/api/versions/share',json={'version_id':self.version.id},headers=guest)).status_code,404)

    async def test_studio_clears_the_old_chat_for_a_remix_and_shares_in_one_tap(self):
        html=(await self.client.get('/v/'+self.version.id)).text
        remix=html.split('const remixing=',1)[1].split('let sessionId=',1)[0]
        self.assertIn("get('remix')==='1'",remix);self.assertIn('localStorage.removeItem(SK.SESSION)',remix)
        self.assertIn("history.replaceState(history.state,'',location.pathname)",remix)
        self.assertIn('<script src="/static/js/share-link.js" defer></script>',html)
        share=html.split('async function handleShare(',1)[1].split('async function handleSuggest(',1)[0]
        self.assertIn('await shareOut();',share);self.assertIn('window.OWShare',share)
        self.assertIn('id="ow-share-native" hidden',html)
        for dash in DASHES:self.assertNotIn(dash,share+remix)

    async def test_share_helper_tries_the_share_sheet_then_the_clipboard(self):
        js=(await self.client.get('/static/js/share-link.js')).text
        self.assertLess(js.index('navigator.share('),js.index('navigator.clipboard.writeText('))
        for result in ["'shared'","'cancelled'","'copied'","'manual'"]:self.assertIn(result,js)


if __name__=='__main__':unittest.main()
