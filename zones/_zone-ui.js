// Zone UI — prompt display and fade overlay
export class ZoneUI {
  constructor(){
    // "Press E to enter" prompt (mirrors #vehicle-prompt pattern)
    this.prompt=document.createElement('div');
    this.prompt.id='zone-prompt';
    this.prompt.style.cssText='position:fixed;bottom:145px;left:50%;transform:translateX(-50%);font-size:0.95em;color:#44aaff;font-family:"Courier New",monospace;opacity:0;transition:opacity 0.3s;text-shadow:0 0 10px rgba(0,150,255,0.4);z-index:6;pointer-events:none';
    document.body.appendChild(this.prompt);

    // Fade overlay for enter/exit transitions
    this.overlay=document.createElement('div');
    this.overlay.id='zone-fade';
    this.overlay.style.cssText='position:fixed;inset:0;background:#000;opacity:0;pointer-events:none;z-index:15;transition:opacity 0.4s';
    document.body.appendChild(this.overlay);
  }

  showPrompt(text){this.prompt.textContent=text;this.prompt.style.opacity='1'}
  hidePrompt(){this.prompt.style.opacity='0'}

  fadeOut(ms=400){
    return new Promise(r=>{
      this.overlay.style.transition=`opacity ${ms}ms`;
      this.overlay.style.opacity='1';
      setTimeout(r,ms);
    });
  }
  fadeIn(ms=400){
    return new Promise(r=>{
      this.overlay.style.transition=`opacity ${ms}ms`;
      this.overlay.style.opacity='0';
      setTimeout(r,ms);
    });
  }
}
