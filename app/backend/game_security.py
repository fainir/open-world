"""Executable game documents always run with an opaque origin."""
from pathlib import Path
from fastapi.responses import HTMLResponse

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


def game_response(path):
    html = Path(path).read_text(encoding='utf-8')
    legacy_store = """fetch('/api/store/random-slug').then(r=>r.json()).then(d=>{
          if(d.share_slug)window.location.href='/shared/'+d.share_slug;
          else showTip('No published games yet!');
        }).catch(()=>showTip('No published games yet!'));"""
    html = html.replace(legacy_store, "if(parent===window)location.href='/';else parent.postMessage({type:'ow-open-store'},'*');")
    return HTMLResponse('<!doctype html>' + EPHEMERAL_STORAGE + html, headers={
        "Content-Security-Policy": GAME_CSP,
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    })


def studio_shell(overlay):
    # No game-controlled bytes are ever interpolated into the credential-bearing parent.
    return '''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Open World Studio</title><style>html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#111;color:#eee;font-family:system-ui}#ow-game{width:100%;height:100%;border:0}#ow-game-error{position:fixed;left:20px;bottom:20px;z-index:99999;padding:15px;background:#222}</style></head>
<body><iframe id="ow-game" title="Game preview" sandbox="allow-scripts allow-pointer-lock" referrerpolicy="no-referrer"></iframe>''' + overlay + '''</body></html>'''
