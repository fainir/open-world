"""Build the CrazyGames upload: the playable base game only, as a self-contained static zip.

    python3 release/crazygames/build.py          -> release/crazygames/openworld-crazygames.zip
    python3 release/crazygames/build.py --sdk    -> release/crazygames/openworld-crazygames-sdk.zip

The zip holds index.html plus the exact Three.js r160 files the live game already loads, so the
game makes no network request at all. There is no AI editor, no link out, no PWA install banner and
no call to open-world.gg. With --sdk it also loads the CrazyGames SDK v3 and reports loading
start/stop and gameplay start/stop; every SDK call is guarded, so the game runs without it.
Standard library only. Three.js is fetched once from the same pinned jsDelivr URLs, checked
against fixed SHA-256 hashes and cached in release/crazygames/.cache (not committed).
"""
import argparse
import hashlib
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CACHE = HERE / '.cache'
THREE = 'https://cdn.jsdelivr.net/npm/three@0.160.0/'
VENDOR = {  # path inside the zip: (source URL, SHA-256)
    'vendor/three/three.module.js': (
        THREE + 'build/three.module.js',
        '76dea8151bc9352aef3528b4262e249b2604f62543828328db978d060d61a495'),
    'vendor/three/addons/utils/BufferGeometryUtils.js': (
        THREE + 'examples/jsm/utils/BufferGeometryUtils.js',
        '9be041e96308775d00e2695cc607645b9a9b64fd7c0e759dd8f7c00a8d92becb'),
}
SDK_URL = 'https://sdk.crazygames.com/crazygames-sdk-v3.js'
FIXED_TIME = (2026, 1, 1, 0, 0, 0)  # same input, same zip bytes

# CrazyGames SDK v3: loading and gameplay events only (docs.crazygames.com/sdk/game/).
# Gameplay runs while the start screen and the pause screen are both hidden.
SDK_BRIDGE = '''<script>
(function(){
  var sdk=null,playing=false;
  function call(name){try{if(sdk)sdk.game[name]()}catch(e){}}
  var ready=(async function(){
    try{var s=window.CrazyGames&&window.CrazyGames.SDK;if(!s)return;await s.init();
      if(s.environment==='disabled')return;sdk=s;call('loadingStart')}catch(e){sdk=null}
  })();
  function sync(){
    var start=document.getElementById('overlay'),pause=document.getElementById('pause-screen');
    var now=!!start&&start.style.display==='none'&&!(pause&&pause.style.display==='flex');
    if(now!==playing){playing=now;call(now?'gameplayStart':'gameplayStop')}
  }
  window.addEventListener('load',function(){ready.then(function(){
    call('loadingStop');
    var watch=new MutationObserver(sync);
    ['overlay','pause-screen'].forEach(function(id){var el=document.getElementById(id);if(el)watch.observe(el,{attributes:true,attributeFilter:['style']})});
    sync();
  })});
})();
</script>
'''


def replace_once(html, old, new, why):
    count = html.count(old)
    if count != 1:
        sys.exit(f'Portal build stopped: expected one match for {why}, found {count}. Update build.py for the new base game.')
    return html.replace(old, new)


def replace_pattern(html, pattern, new, why, must_contain):
    found = re.findall(pattern, html, flags=re.S)
    if len(found) != 1 or must_contain not in found[0]:
        sys.exit(f'Portal build stopped: expected one match for {why}, found {len(found)}. Update build.py for the new base game.')
    return re.sub(pattern, lambda _: new, html, flags=re.S)


def portal_html(source, sdk):
    html = source
    # 1. Three.js from the zip itself, by relative path (CrazyGames: never absolute paths).
    html = replace_once(
        html,
        '{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",'
        '"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}',
        '{"imports":{"three":"./vendor/three/three.module.js","three/addons/":"./vendor/three/addons/"}}',
        'the Three.js import map')
    # 2. No cache-busting reload; that was for our own site.
    html = replace_pattern(html, r'<script>\n// Force reload if user has outdated cached version\n.*?</script>\n', '',
                           'the cache-busting reload', "location.reload(true)")
    # 3. No portal to other people's games on open-world.gg (no cross-promotion, no external call).
    html = replace_pattern(
        html,
        r"const _spDx=P\.x-_storePortalPos\.x.*?else\{const nv=nearestVehicle\(\);if\(nv\)mountVehicle\(nv\)\}",
        '{const nv=nearestVehicle();if(nv)mountVehicle(nv)}', 'the Game Store portal action', '/api/store/random-slug')
    html = replace_once(html, '_storePortalGroup.visible=d2<40000;', '_storePortalGroup.visible=false;', 'the portal ring')
    html = replace_once(html, 'function updateStorePortalMarker(){', "function updateStorePortalMarker(){_spMarker.style.opacity='0';return;",
                        'the portal marker')
    # 4. No install-the-app banner or web app manifest.
    html = replace_once(html, '(function(){\n  // Create manifest dynamically for PWA', '(function(){return;\n  // Create manifest dynamically for PWA',
                        'the install banner')
    # 5. CrazyGames owns fullscreen; the game must not request it on start.
    html = replace_once(html, "if(goFS){try{goFS.call(de).catch(()=>{})}catch(e){}}", '', 'fullscreen on start')
    # 6. PEGI 12: light hit puffs instead of red blood.
    html = replace_once(html, 'new THREE.MeshBasicMaterial({color:0xcc0000,transparent:true,opacity:0.9})',
                        'new THREE.MeshBasicMaterial({color:0xe8e8e8,transparent:true,opacity:0.9})', 'the hit particles')
    # 7. Mobile: no text selection or callout on long press (CrazyGames technical requirements).
    html = replace_once(html, 'body{overflow:hidden;background:#000;',
                        'body{overflow:hidden;background:#000;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;',
                        'body style')
    html = replace_once(html, '<title>Open World</title>', '<title>Open World City Sandbox</title>', 'the title')
    if sdk:
        html = replace_once(html, '<script type="importmap">', f'<script src="{SDK_URL}"></script>\n<script type="importmap">', 'SDK script')
        html = replace_once(html, '</body>', SDK_BRIDGE + '</body>', 'the end of body')
    # Nothing left that reaches our backend, the editor or another site.
    for banned in ['open-world.gg', '/api/', 'fetch(', 'cdn.jsdelivr.net', 'unpkg.com', 'window.open', 'ow-open-store', 'location.href=']:
        if banned in html:
            sys.exit(f'Portal build stopped: "{banned}" is still in the game.')
    return html


def vendor_file(name):
    url, digest = VENDOR[name]
    cached = CACHE / name
    if not cached.exists():
        cached.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as response:
            cached.write_bytes(response.read())
    data = cached.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        cached.unlink()
        sys.exit(f'Portal build stopped: {url} does not match its pinned SHA-256.')
    return data


def build(sdk):
    html = portal_html((ROOT / 'index.html').read_text(encoding='utf-8'), sdk)
    files = {'index.html': html.encode('utf-8'), **{name: vendor_file(name) for name in VENDOR}}
    for name, data in files.items():
        if name.endswith('.js') and re.search(rb'^\s*import[^;]*from\s*["\'](https?:|/)', data, flags=re.M):
            sys.exit(f'Portal build stopped: {name} imports from an absolute URL.')
    target = HERE / ('openworld-crazygames-sdk.zip' if sdk else 'openworld-crazygames.zip')
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[name])
    total = sum(len(data) for data in files.values())
    print(f'{target.relative_to(ROOT)}: {target.stat().st_size:,} bytes zipped, {total:,} bytes unzipped, {len(files)} files')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--sdk', action='store_true', help='portal flag: add CrazyGames SDK v3 loading and gameplay events')
    build(parser.parse_args().sdk)
