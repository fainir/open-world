"""CrazyGames upload: base game only, self-contained, nothing that reaches open-world.gg. No network."""
import hashlib,importlib.util,json,re,unittest,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'release'/'crazygames'
spec=importlib.util.spec_from_file_location('crazygames_build',HERE/'build.py');build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
BANNED=['open-world.gg','/api/','fetch(','cdn.jsdelivr.net','unpkg.com','window.open','ow-open-store','location.href=','overlay.html','ow_api_key']


class CrazyGamesZip(unittest.TestCase):
    def read(self,name):
        with zipfile.ZipFile(HERE/name) as archive:
            return {info.filename:archive.read(info) for info in archive.infolist()}

    def test_both_zips_hold_only_the_base_game_and_pinned_three(self):
        for name,sdk in [('openworld-crazygames.zip',False),('openworld-crazygames-sdk.zip',True)]:
            with self.subTest(zip=name):
                files=self.read(name)
                self.assertEqual(sorted(files),['index.html','vendor/three/addons/utils/BufferGeometryUtils.js','vendor/three/three.module.js'])
                for path,(_,digest) in build.VENDOR.items():self.assertEqual(hashlib.sha256(files[path]).hexdigest(),digest,path)
                self.assertLess(sum(map(len,files.values())),20*1024*1024)  # mobile homepage initial download limit
                html=files['index.html'].decode()
                for banned in BANNED:self.assertNotIn(banned,html)
                imports=json.loads(re.search(r'<script type="importmap">\s*(\{.*?\})\s*</script>',html,re.S).group(1))['imports']
                self.assertEqual(imports,{'three':'./vendor/three/three.module.js','three/addons/':'./vendor/three/addons/'})
                self.assertIn('(function(){return;\n  // Create manifest dynamically for PWA',html)  # install banner off
                self.assertIn("_storePortalGroup.visible=false;",html);self.assertNotIn('0xcc0000,transparent:true,opacity:0.9',html)
                self.assertIn('crazygames-sdk-v3.js',html) if sdk else self.assertNotIn('crazygames',html.lower())
                if sdk:
                    for call in ['init()','loadingStart','loadingStop','gameplayStart','gameplayStop']:self.assertIn(call,html)

    def test_the_build_still_applies_to_the_current_base_game(self):
        for sdk in [False,True]:
            html=build.portal_html((ROOT/'index.html').read_text(encoding='utf-8'),sdk)
            for banned in BANNED:self.assertNotIn(banned,html)
            self.assertIn('<title>Open World City Sandbox</title>',html)


if __name__=='__main__':unittest.main()
