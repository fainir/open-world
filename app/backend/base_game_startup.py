"""Expose the first-party game's Start control after its module initializes."""

PROMPT = '<div class="click">Click or press anything to start</div>'
MODULE = '<script type="module">'
START_GAME = 'function startGame(){\n'
KEYBOARD_START = "document.addEventListener('keydown',()=>{if(overlay.style.display!=='none'&&!gameStarted)startGame()},{once:true});"
MOBILE_INPUT = "const isMobile='ontouchstart' in window&&navigator.maxTouchPoints>0;"
MODULE_END = '</script>\n</body>\n</html>'

STARTUP = '''<style>
#overlay:has(#ow-base-status:not([hidden])){cursor:default}
#overlay #ow-base-status{color:#fff;text-align:center;margin:0 16px 12px}
#overlay .ow-base-action{min-height:44px;padding:8px 16px;border:1px solid #8396af;
border-radius:8px;background:#203550;color:#fff;font:inherit;cursor:pointer;animation:none}
#overlay .ow-base-action:focus-visible{outline:3px solid #a9c6ff;outline-offset:3px}
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


def with_base_startup(html: str) -> str:
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
    html = html.replace(START_GAME, START_GAME + "  if(document.getElementById('ow-base-play').hidden)return;\n", 1)
    # The native button handles Enter and Space without catching Tab or Escape.
    html = html.replace(KEYBOARD_START, '', 1)
    # The opaque Remix frame can report a touchscreen without exposing ontouchstart.
    html = html.replace(MOBILE_INPUT,
                        "const isMobile=navigator.maxTouchPoints>0&&('ontouchstart' in window||matchMedia('(pointer: coarse)').matches);", 1)
    # Some browsers reject pointer lock asynchronously. The canvas can retry on a click.
    html = html.replace("try{canvas.requestPointerLock()}catch(e){}",
                        "try{canvas.requestPointerLock()?.catch?.(()=>{})}catch(e){}")
    return html.replace(MODULE_END, "document.dispatchEvent(new Event('ow-base-ready'));\n" + MODULE_END, 1)
