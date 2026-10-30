"""Executable game documents always run with an opaque origin."""
from html import escape
from pathlib import Path
from urllib.parse import quote
from fastapi.responses import HTMLResponse

PUBLIC_ORIGIN = 'https://open-world.gg'
# No per-game screenshot is stored yet, so every shared game uses the landing card.
SHARE_IMAGE = PUBLIC_ORIGIN + '/static/og-card.png'
SHARE_IMAGE_ALT = 'Open World gameplay: gliding over a 3D city toward snowy mountains'
SHARED_TITLE_FALLBACK = 'A game made in OpenWorld'
SHARED_DESCRIPTION_FALLBACK = 'Play this 3D browser game made with AI in OpenWorld, then describe your own change.'

# Legacy games use Web Storage for cosmetic preferences. Opaque documents cannot
# access origin storage; give each document an empty, bounded, in-memory substitute.
EPHEMERAL_STORAGE = '''<script>(function(){for(const name of ['localStorage','sessionStorage']){try{window[name].getItem('__ow_storage_probe')}catch{const values=new Map();const storage={getItem:k=>values.has(String(k))?values.get(String(k)):null,setItem(k,v){k=String(k);v=String(v);if(k.length+v.length>16384||values.size>=100)throw new Error('Game preference limit');values.set(k,v)},removeItem:k=>values.delete(String(k)),clear:()=>values.clear(),key:i=>Array.from(values.keys())[i]??null,get length(){return values.size}};Object.defineProperty(window,name,{value:storage})}}})();</script>'''

GAME_CSP = (
    "sandbox allow-scripts allow-pointer-lock; default-src 'none'; "
    "script-src 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
    "style-src 'unsafe-inline'; img-src data: blob:; "
    "connect-src https://cdn.jsdelivr.net https://unpkg.com; "
    "font-src data:; media-src blob:; worker-src blob:; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
)


def _share_text(value, limit):
    text = ' '.join(''.join(c for c in str(value or '') if c.isprintable() or c.isspace()).split())
    return text if len(text) <= limit else text[:limit - 3].rstrip() + '...'


def shared_game_head(share_slug, title, description):
    """Share-card tags for one explicitly shared game. Titles and descriptions come from users."""
    title = _share_text(title, 90) or SHARED_TITLE_FALLBACK
    description = _share_text(description, 200) or SHARED_DESCRIPTION_FALLBACK
    values = [('property', 'og:type', 'website'), ('property', 'og:site_name', 'Open World'),
              ('property', 'og:title', title), ('property', 'og:description', description),
              ('property', 'og:url', PUBLIC_ORIGIN + '/shared/' + quote(str(share_slug), safe='')),
              ('property', 'og:image', SHARE_IMAGE), ('property', 'og:image:type', 'image/png'),
              ('property', 'og:image:width', '1200'), ('property', 'og:image:height', '630'),
              ('property', 'og:image:alt', SHARE_IMAGE_ALT), ('name', 'description', description),
              ('name', 'twitter:card', 'summary_large_image'), ('name', 'twitter:title', title),
              ('name', 'twitter:description', description), ('name', 'twitter:image', SHARE_IMAGE),
              ('name', 'twitter:image:alt', SHARE_IMAGE_ALT)]
    return '<meta charset="utf-8">' + ''.join(
        '<meta %s="%s" content="%s">' % (kind, key, escape(value, quote=True)) for kind, key, value in values)


def game_response(path, head=''):
    html = Path(path).read_text(encoding='utf-8')
    legacy_store = """fetch('/api/store/random-slug').then(r=>r.json()).then(d=>{
          if(d.share_slug)window.location.href='/shared/'+d.share_slug;
          else showTip('No published games yet!');
        }).catch(()=>showTip('No published games yet!'));"""
    html = html.replace(legacy_store, "if(parent===window)location.href='/';else parent.postMessage({type:'ow-open-store'},'*');")
    return HTMLResponse('<!doctype html>' + head + EPHEMERAL_STORAGE + html, headers={
        "Content-Security-Policy": GAME_CSP,
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    })


def game_error_response():
    return HTMLResponse('''<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Game temporarily unavailable</title><style>body{background:#111827;color:#e8edf6;font:16px/1.6 system-ui;padding:24px;max-width:620px}button{font:inherit;min-height:44px;padding:10px 18px;background:#dbe7ff;color:#14203a;border:0;border-radius:8px}button:focus-visible{outline:3px solid #9ebcff;outline-offset:3px}</style><main><h1>Game temporarily unavailable</h1><p role="alert">The game file could not load. Your saved account data has not changed.</p><button onclick="location.reload()">Try loading the game again</button></main></html>''',status_code=404,headers={'Content-Security-Policy':GAME_CSP,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'})


def studio_shell(overlay):
    # No game-controlled bytes are ever interpolated into the credential-bearing parent.
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Open World - a 3D browser game you can change with AI</title>
<meta name="description" content="Play a 3D open world in your browser: drive, glide and explore a city, beach and mountains. Describe a change, AI edits the game, and share your version.">
<link rel="canonical" href="https://open-world.gg/">
<meta name="google-site-verification" content="2_cyzqDDncUndfZBOwHOEn7slsNsTk2tu-ZAgeeGxd0">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Open World">
<meta property="og:title" content="Open World - a 3D browser game you can change with AI">
<meta property="og:description" content="Play a 3D open world in your browser: drive, glide and explore a city, beach and mountains. Describe a change, AI edits the game, and share your version.">
<meta property="og:url" content="https://open-world.gg/">
<meta property="og:image" content="https://open-world.gg/static/og-card.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Open World gameplay: gliding over a 3D city toward snowy mountains">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Open World - a 3D browser game you can change with AI">
<meta name="twitter:description" content="Play a 3D open world in your browser: drive, glide and explore a city, beach and mountains. Describe a change, AI edits the game, and share your version.">
<meta name="twitter:image" content="https://open-world.gg/static/og-card.png">
<meta name="twitter:image:alt" content="Open World gameplay: gliding over a 3D city toward snowy mountains">
<style>html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#111;color:#eee;font-family:system-ui}#ow-game-view{width:100%;height:100%}#ow-game{width:100%;height:100%;border:0}#ow-game-error{position:fixed;left:20px;bottom:20px;z-index:99999;padding:15px;background:#222}</style></head>
<body><main id="ow-game-view" aria-label="Game preview"><iframe id="ow-game" title="Game preview" allowfullscreen sandbox="allow-scripts allow-pointer-lock" referrerpolicy="no-referrer"></iframe></main>''' + overlay + '''</body></html>'''
