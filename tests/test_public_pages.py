"""Public marketing pages over ASGI. No account, provider or network request."""
import os
import unittest
from unittest.mock import patch
from xml.etree import ElementTree
import test_security  # installs the existing disposable SQLite environment first
from test_security import _Document
import httpx
from app.backend.database import init_db
from app.backend.main import app

PAGE = 'https://open-world.gg/rosebud-alternative'
DASHES = ['–', '—', '&ndash;', '&mdash;', '&#8211;', '&#8212;', '&#x2013;', '&#x2014;']


class RosebudAlternative(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        init_db()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='https://open-world.gg')

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_page_has_its_own_canonical_metadata_and_required_sections(self):
        r = await self.client.get('/rosebud-alternative')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.headers['content-type'].startswith('text/html'))
        doc = _Document(r.text)
        self.assertEqual([a.get('href') for t, a in doc.tags if t == 'link' and a.get('rel') == 'canonical'], [PAGE])
        self.assertEqual([t for t, _ in doc.tags].count('h1'), 1)
        title = r.text.split('<title>', 1)[1].split('</title>', 1)[0]
        self.assertTrue(title.startswith('Rosebud AI alternative'), title)
        for key in ['description', 'og:description', 'twitter:description']:
            self.assertIn('Rosebud AI alternative', doc.meta(key)[0], key)
        self.assertEqual(doc.meta('og:title'), [title]); self.assertEqual(doc.meta('twitter:title'), [title])
        self.assertEqual(doc.meta('og:url'), [PAGE])
        self.assertEqual(doc.meta('og:image'), ['https://open-world.gg/static/og-card.png'])
        self.assertEqual(doc.meta('twitter:card'), ['summary_large_image'])
        for text in ['1 November 2026', 'Where Rosebud is stronger', 'Who should pick which',
                     'Rosebud is a trademark of its owner. OpenWorld is not affiliated with Rosebud.']:
            self.assertIn(text, r.text)

    async def test_page_and_its_new_links_contain_no_en_or_em_dashes(self):
        pages = {'page': (await self.client.get('/rosebud-alternative')).text,
                 'sitemap': (await self.client.get('/sitemap.xml')).text}
        for name, text in pages.items():
            for dash in DASHES:
                self.assertNotIn(dash, text, name)

    async def test_sitemap_lists_the_page_and_the_home_footer_links_to_it(self):
        r = await self.client.get('/sitemap.xml')
        self.assertEqual(r.status_code, 200)
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locs = [e.text for e in ElementTree.fromstring(r.content).findall('s:url/s:loc', ns)]
        self.assertIn(PAGE, locs)
        self.assertEqual(len(locs), len(set(locs)))
        home = _Document((await self.client.get('/')).text)
        self.assertIn('/rosebud-alternative', [a.get('href') for t, a in home.tags if t == 'a'])

    async def test_default_railway_host_moves_the_page_to_the_real_domain(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url='https://open-world-studio-production.up.railway.app') as client:
            with patch.dict(os.environ, {'RAILWAY_ENVIRONMENT_NAME': 'production'}):
                r = await client.get('/rosebud-alternative')
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.headers['location'], PAGE)


if __name__ == '__main__': unittest.main(verbosity=2)
