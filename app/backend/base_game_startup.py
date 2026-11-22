"""Start the first-party game only after its playing surface is ready."""

PROMPT = '<div class="click">Click or press anything to start</div>'
MODULE = '<script type="module">'
START_GAME = 'function startGame(){\n'
IMMERSIVE_START = '  if(!isMobile)try{canvas.requestPointerLock()}catch(e){}'
KEYBOARD_START = "document.addEventListener('keydown',()=>{if(overlay.style.display!=='none'&&!gameStarted)startGame()},{once:true});"
MOBILE_INPUT = "const isMobile='ontouchstart' in window&&navigator.maxTouchPoints>0;"
MODULE_END = '</script>\n</body>\n</html>'
ROTATION_EVENTS = """    window.dispatchEvent(new Event('resize'));
  }
  _applyRotation();
  window.addEventListener('orientationchange',()=>setTimeout(_applyRotation,100));
  window.matchMedia('(orientation:portrait)').addEventListener('change',()=>setTimeout(_applyRotation,50));"""

TOUCH_FULLSCREEN = """  const fsBtn=document.getElementById('btn-fs');
  fsBtn.addEventListener('touchstart',e=>{
    e.preventDefault();e.stopPropagation();
    const de=document.documentElement;
    if(document.fullscreenElement||document.webkitFullscreenElement){
      (document.exitFullscreen||document.webkitExitFullscreen).call(document).catch(()=>{});
    }else{
      (de.requestFullscreen||de.webkitRequestFullscreen||de.msRequestFullscreen).call(de).catch(()=>{});
    }
  },{passive:false});"""

PLAY_KEYS = """
async function toggleGameFullscreen(){
  try{
    if(document.fullscreenElement||document.webkitFullscreenElement){
      await (document.exitFullscreen||document.webkitExitFullscreen)?.call(document);return;
    }
    const root=document.documentElement;
    if(root.requestFullscreen)await root.requestFullscreen({navigationUI:'hide'});
    else await root.webkitRequestFullscreen?.();
    if(isMobile&&(document.fullscreenElement||document.webkitFullscreenElement))await screen.orientation?.lock?.('landscape');
  }catch{}
}
document.getElementById('btn-fs').addEventListener('click',toggleGameFullscreen);
document.addEventListener('keydown',event=>{
  if(!gameStarted||event.repeat||event.ctrlKey||event.metaKey||event.altKey)return;
  if(event.code==='KeyG'){
    event.preventDefault();void toggleGameFullscreen();
  }
  if(event.code==='KeyX'&&!gamePaused&&!menuOpen&&!wpnMenuOpen&&!charMenuOpen)keys._keyboardShoot=keys['_shooting']=true;
});
document.addEventListener('keyup',event=>{if(event.code==='KeyX')keys._keyboardShoot=keys['_shooting']=false;});
window.addEventListener('blur',()=>{keys._keyboardShoot=keys['_shooting']=false;});
"""

STARTUP = '''<style>
#overlay:has(#ow-base-status:not([hidden])){cursor:default}
#overlay #ow-base-status{color:#fff;text-align:center;margin:0 16px 12px}
#overlay .ow-base-action{min-height:44px;padding:8px 16px;border:1px solid #8396af;
border-radius:8px;background:#203550;color:#fff;font:inherit;cursor:pointer;animation:none}
#overlay .ow-base-action:focus-visible{outline:3px solid #a9c6ff;outline-offset:3px}
.mobile.playing #btn-fs{display:grid!important;place-items:center;position:fixed;z-index:9;
top:12px;right:154px;width:44px;height:44px;border:2px solid #ffffff40;border-radius:50%;
color:#fff;background:#0009;font-size:20px;touch-action:manipulation}
.mobile.playing #btn-pause{right:62px;width:44px;height:44px}
.mobile.playing #pwa-install{right:112px}
.mobile.playing .mc-btn{box-sizing:border-box;min-width:44px;min-height:44px}
.mobile.playing :is(#veh-menu,#wpn-menu,#char-menu){box-sizing:border-box;max-width:calc(100% - 24px);max-height:calc(100% - 24px)}
.mobile.playing :is(#veh-close,#wpn-close,#char-close){min-width:44px;min-height:44px;display:grid;place-items:center}
.mobile.playing #char-close{left:6px;right:auto;margin:0}
.mobile.playing #char-menu h2{min-height:32px;padding-inline:46px 6px}
@media(pointer:fine){.mobile.playing #bottom-bar{display:flex!important}}
@media(max-width:500px){
  #overlay h1{max-width:calc(100% - 32px);font-size:clamp(1.5rem,7vw,2.5rem);
  letter-spacing:.12em;text-align:center;overflow-wrap:anywhere}
}
</style>
<p id="ow-base-status" role="status">Loading game…</p>
<button type="button" id="ow-base-play" class="click ow-base-action" hidden>Start game</button>
<button type="button" id="ow-base-retry" class="ow-base-action" hidden>Retry</button>
<script>
(() => {
  const status = document.getElementById('ow-base-status');
  const play = document.getElementById('ow-base-play');
  const retry = document.getElementById('ow-base-retry');
  window.addEventListener('error', event => {
    if (play.hidden && (event.target?.id === 'ow-base-module' || event instanceof ErrorEvent)) {
      status.textContent = 'The game could not load.';
      retry.hidden = false;
    }
  }, true);
  document.addEventListener('ow-base-ready', () => {
    status.hidden = true;
    retry.hidden = true;
    play.hidden = false;
  }, { once: true });
  const stopGameInput = event => event.stopPropagation();
  play.addEventListener('keydown', stopGameInput);
  retry.addEventListener('keydown', stopGameInput);
  retry.addEventListener('touchstart', stopGameInput);
  retry.addEventListener('click', event => {
    event.stopPropagation();
    location.reload();
  });
})();
</script>'''


def with_base_startup(html: str, *, autoplay: bool = False) -> str:
    # The persisted owner template can predate a deploy. Match its known
    # startup shape before inserting anything into the response.
    markers = (PROMPT, MODULE, START_GAME, KEYBOARD_START, MODULE_END)
    if any(html.count(marker) != 1 for marker in markers):
        return html
    prompt, module, start, keys, end = (html.index(marker) for marker in markers)
    if not prompt < module < start < keys < end or html.find('</script>', module) != end:
        return html
    html = html.replace(PROMPT, STARTUP, 1)
    html = html.replace(MODULE, '<script type="module" id="ow-base-module">', 1)
    html = html.replace(START_GAME, "function startGame(immersive=true){\n  if(document.getElementById('ow-base-play').hidden)return;\n", 1)
    # The native button handles Enter and Space without catching Tab or Escape.
    html = html.replace(KEYBOARD_START, '', 1)
    # The opaque Remix frame can report a touchscreen without exposing ontouchstart.
    html = html.replace(MOBILE_INPUT,
                        "const isMobile=navigator.maxTouchPoints>0||matchMedia('(any-pointer: coarse)').matches;", 1)
    # Only the interactive start attempts browser permissions. The home launch
    # reaches the same flying state as the Start button.
    immersive = html.index(IMMERSIVE_START, start) if IMMERSIVE_START in html[start:] else -1
    if immersive >= 0:
        html = html[:immersive] + "  if(!immersive)return;\n" + html[immersive:]
    html = html.replace("function _isPortrait(){const w=_origIW.get.call(window),h=_origIH.get.call(window);return h>w}",
                        "function _isPortrait(){const w=_origIW.get.call(window),h=_origIH.get.call(window);return h>w&&(w<750||matchMedia('(pointer: coarse)').matches)}", 1)
    html = html.replace(ROTATION_EVENTS, "  }\n  _applyRotation();\n  window.addEventListener('resize',_applyRotation);", 1)
    rotated = "document.body.style.transform==='rotate(90deg)'"
    html = html.replace("let dx=tx-joyCX,dy=ty-joyCY;",
                        "let dx=tx-joyCX,dy=ty-joyCY;\n    if(" + rotated + ")[dx,dy]=[dy,-dx];", 1)
    html = html.replace("const dx=t.clientX-camLastX,dy=t.clientY-camLastY;",
                        "let dx=t.clientX-camLastX,dy=t.clientY-camLastY;\n        if(" + rotated + ")[dx,dy]=[dy,-dx];", 1)
    if TOUCH_FULLSCREEN in html:
        html = html.replace(TOUCH_FULLSCREEN, '', 1)
        html = html.replace('<div id="btn-fs">&#x26F6;</div>',
                            '<button type="button" id="btn-fs" aria-label="Full screen" aria-keyshortcuts="G">&#x26F6;</button>', 1)
        html = html.replace('<div id="controls-bar">', '<div id="controls-bar">\n'
                            '<span class="ctrl-key"><kbd>G</kbd><span class="cl">Full screen</span></span>'
                            '<span class="ctrl-key"><kbd>Esc</kbd><span class="cl">Pause</span></span>', 1)
        html = html.replace('<kbd>Click</kbd>', '<kbd>X</kbd> / <kbd>Click</kbd>')
        html = html.replace('if(shooting&&fireCooldown<=0&&locked){',
                            'if((shooting||keys._keyboardShoot)&&fireCooldown<=0&&locked&&!gamePaused&&!menuOpen&&!wpnMenuOpen&&!charMenuOpen){', 1)
        html = html.replace(MODULE_END, PLAY_KEYS + MODULE_END, 1)
    # Some browsers reject pointer lock asynchronously. The canvas can retry on a click.
    html = html.replace("try{canvas.requestPointerLock()}catch(e){}",
                        "try{canvas.requestPointerLock()?.catch?.(()=>{})}catch(e){}")
    ready = "document.dispatchEvent(new Event('ow-base-ready'));\n"
    if autoplay and immersive >= 0:
        ready += "startGame(false);\n"
    return html.replace(MODULE_END, ready + MODULE_END, 1)
