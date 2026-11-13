from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.backend.base_game_startup import MOBILE_INPUT, with_base_startup
from app.backend.game_security import GAME_CSP, game_response


class BaseStartupTests(unittest.TestCase):
    def test_known_demo_response_keeps_disk_and_shared_game_unchanged(self):
        with TemporaryDirectory() as directory:
            game = Path(directory) / 'base.html'
            game.write_bytes(Path('index.html').read_bytes())
            original = game.read_bytes()

            base = game_response(game, base_demo=True)
            shared = game_response(game)

            self.assertIn(b'Loading game', base.body)
            self.assertIn(b'id="ow-base-module"', base.body)
            self.assertIn(b"document.dispatchEvent(new Event('ow-base-ready'))", base.body)
            self.assertIn(b"matchMedia('(pointer: coarse)').matches", base.body)
            self.assertIn(b'Click or press anything to start', shared.body)
            self.assertIn(MOBILE_INPUT.encode(), shared.body)
            self.assertNotIn(b'ow-base-ready', shared.body)
            self.assertEqual(base.headers['Content-Security-Policy'], GAME_CSP)
            self.assertEqual(dict(base.headers.items()) | {'content-length': ''},
                             dict(shared.headers.items()) | {'content-length': ''})
            self.assertEqual(game.read_bytes(), original)

    def test_unknown_or_split_module_is_unchanged(self):
        original = Path('index.html').read_text(encoding='utf-8')
        for game in (
            '<html><body>Other game</body></html>',
            original.replace('</body>', '<script>console.log("later")</script>\n</body>', 1),
        ):
            with self.subTest(size=len(game)):
                self.assertEqual(with_base_startup(game), game)
