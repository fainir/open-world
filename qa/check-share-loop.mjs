// Shared game page share loop, like a visitor: Made with link, Remix this, one-tap share, game start.
// Read-only: every non-GET request is aborted, so no AI edit, share, star or account write can happen.
// Picks the newest game from the public games list. The share sheet itself cannot open in headless
// Chrome, so it is replaced by a recorder; copy uses the real clipboard.
// Usage: node qa/check-share-loop.mjs <base-url> <playwright/index.mjs> [out-dir]
import assert from 'node:assert/strict';import {mkdir} from 'node:fs/promises';import {pathToFileURL} from 'node:url';
const base=process.argv[2].replace(/\/$/,''),out=process.argv[4]||'qa/share-loop';
const {chromium}=await import(pathToFileURL(process.argv[3]).href);await mkdir(out,{recursive:true});
const allowed=new Set([base,'https://cdn.jsdelivr.net','https://unpkg.com']);
const list=await (await fetch(base+'/api/store/versions?sort=recent&page=0&limit=20')).json();
const game=list.versions.find(v=>v.share_slug);assert.ok(game,'a public shared game exists');
const shareUrl=base+'/shared/'+game.share_slug;console.log('Public game:',JSON.stringify({title:game.title,slug:game.share_slug}));
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:['--enable-unsafe-swiftshader']});
const widths=[[375,{viewport:{width:375,height:812},isMobile:true,hasTouch:true}],[1440,{viewport:{width:1440,height:900}}]];

async function open(options,mode){
 const c=await browser.newContext({...options,permissions:mode==='copy'?['clipboard-read','clipboard-write']:[]});
 const t={c,errors:[],writes:[],external:new Set()};
 await c.addInitScript(mode=>{
  if(window!==top)return;// The opaque game frame rejects storage on purpose.
  localStorage.setItem('openworld.analytics.v1','off');
  // A returning visitor's old chat must not block a remix.
  if(location.pathname.startsWith('/v/'))localStorage.setItem('ow_session_id','qa-old-session');
  window.__shares=[];
  if(mode==='sheet')Object.defineProperty(Navigator.prototype,'share',{configurable:true,value:async data=>{window.__shares.push(data)}});
  else Object.defineProperty(Navigator.prototype,'share',{configurable:true,value:undefined});
  if(mode==='blocked'){Object.defineProperty(Navigator.prototype,'clipboard',{configurable:true,get:()=>({writeText:()=>Promise.reject(Object.assign(new Error('blocked'),{name:'NotAllowedError'}))})});
   Document.prototype.execCommand=()=>false;}
 },mode);
 await c.route('**/*',route=>{const r=route.request(),u=new URL(r.url());
  if(r.method()!=='GET'&&r.method()!=='HEAD'){t.writes.push(r.method()+' '+u.pathname);return route.abort();}
  if(!allowed.has(u.origin)){t.external.add(u.origin);return route.abort();}
  return route.continue();});
 t.p=await c.newPage();t.p.setDefaultTimeout(90000);
 t.p.on('pageerror',e=>t.errors.push('pageerror: '+e.message));
 t.p.on('console',m=>{if(m.type()==='error')t.errors.push('console: '+m.text())});
 return t;
}
async function bar(p,width){
 await p.goto(shareUrl,{waitUntil:'domcontentloaded'});
 const made=p.getByRole('link',{name:'Made with OpenWorld - make your own'}),remix=p.getByRole('link',{name:'Remix this'}),share=p.getByRole('button',{name:'Share',exact:true});
 for(const el of [made,remix,share])await el.waitFor();
 assert.equal(await made.getAttribute('href'),'/');assert.equal(await remix.getAttribute('href'),'/remix/'+game.share_slug);
 for(const el of [made,remix,share]){const b=await el.boundingBox();assert.ok(b.height>=44&&b.width>=44,width+' 44px target '+JSON.stringify(b));assert.ok(b.x>=0&&b.x+b.width<=width,width+' inside viewport');}
 const head=await p.locator('.ow-bar').boundingBox(),frame=await p.locator('#ow-game').boundingBox(),vh=p.viewportSize().height;
 assert.ok(frame.y>=head.y+head.height-1,'game frame starts below the bar');assert.ok(Math.abs(frame.y+frame.height-vh)<=1,'game fills the rest');
 assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,width+' no horizontal scroll');
 assert.equal(await p.locator('#ow-game').getAttribute('sandbox'),'allow-scripts allow-pointer-lock');
 return {made,remix,share};
}

try{for(const [width,options] of widths){
 // 1. The page, the game inside it, and the native share sheet.
 const a=await open(options,'sheet'),p=a.p;const {share}=await bar(p,width);
 const g=p.frameLocator('#ow-game');await g.locator('#overlay').waitFor({state:'visible'});await g.locator('canvas').waitFor({state:'attached'});
 assert.equal(await g.locator('body').evaluate(()=>{try{parent.localStorage.getItem('ow_token');return 'readable'}catch{return 'blocked'}}),'blocked');
 if(width===1440)await p.waitForFunction(()=>document.activeElement&&document.activeElement.id==='ow-game',null,{timeout:30000});// keys go to the game
 await p.screenshot({path:`${out}/shared-${width}.png`});
 await share.click();await p.waitForFunction(()=>window.__shares.length===1);
 const sent=await p.evaluate(()=>window.__shares[0]);assert.equal(sent.url,shareUrl);assert.equal(sent.title,game.title||'A game made in OpenWorld');
 assert.equal(await p.locator('#ow-copy').isVisible(),false);
 // The game still starts and plays inside the page.
 if(width===375){await g.locator('body.mobile').waitFor({state:'attached'});await g.locator('#overlay').tap();}
 else await g.locator('#overlay').click();
 await g.locator('#overlay').waitFor({state:'hidden'});assert.equal(await g.locator('#hud').evaluate(el=>getComputedStyle(el).display),'block');
 if(await g.locator('body').evaluate(()=>!!document.fullscreenElement))await g.locator('body').evaluate(()=>document.exitFullscreen());
 await p.waitForTimeout(1500);await p.screenshot({path:`${out}/shared-playing-${width}.png`});
 console.log(`${width}: bar, 44px targets, game below bar, opaque frame, start/HUD and share sheet (${sent.url}) pass`);
 // 2. Made with OpenWorld goes to the home page.
 await p.getByRole('link',{name:'Made with OpenWorld - make your own'}).click();await p.waitForURL(base+'/');
 assert.equal(await p.locator('#ow-game').getAttribute('src'),'/game/base');
 // 3. Remix this opens the editor on that version, with a fresh chat.
 await bar(p,width);await p.getByRole('link',{name:'Remix this'}).click();
 await p.waitForURL(u=>u.pathname==='/v/'+game.id);assert.equal(new URL(p.url()).search,'','remix flag is removed after use');
 assert.equal(await p.evaluate(()=>localStorage.getItem('ow_session_id')),null,'old chat cleared for the remix');
 await p.locator('#ow-toast.ow-show',{hasText:'Remix: describe a change and it becomes your own copy.'}).waitFor();
 await p.frameLocator('#ow-game').locator('canvas').waitFor({state:'attached'});
 await p.locator('#ow-vdrop-btn',{hasText:game.title||game.description}).waitFor();
 await p.screenshot({path:`${out}/remix-${width}.png`});
 assert.deepEqual(a.writes,[],'no writes');assert.deepEqual([...a.external],[]);
 assert.deepEqual(a.errors,[],'no page or console errors');await a.c.close();
 console.log(`${width}: Made with link to home, Remix to /v/${game.id} with old chat cleared and game loaded pass`);
 // 4. No share sheet: the link is copied (real clipboard).
 const b=await open(options,'copy');await bar(b.p,width);await b.p.getByRole('button',{name:'Share',exact:true}).click();
 await b.p.locator('#ow-status',{hasText:'Link copied'}).waitFor();assert.equal(await b.p.evaluate(()=>navigator.clipboard.readText()),shareUrl);
 await b.p.screenshot({path:`${out}/copied-${width}.png`});assert.deepEqual(b.errors,[]);assert.deepEqual(b.writes,[]);await b.c.close();
 // 5. Clipboard blocked too: the link is shown, selected, to copy by hand.
 const d=await open(options,'blocked');await bar(d.p,width);await d.p.getByRole('button',{name:'Share',exact:true}).click();
 await d.p.locator('#ow-copy').waitFor({state:'visible'});assert.equal(await d.p.locator('#ow-copy-link').inputValue(),shareUrl);
 assert.equal(await d.p.evaluate(()=>document.activeElement.id),'ow-copy-link');
 const box=await d.p.locator('#ow-copy').boundingBox();assert.ok(box.x>=0&&box.x+box.width<=width,'copy box fits');
 await d.p.screenshot({path:`${out}/copy-box-${width}.png`});await d.p.keyboard.press('Escape');await d.p.locator('#ow-copy').waitFor({state:'hidden'});
 assert.deepEqual(d.errors,[]);assert.deepEqual(d.writes,[]);await d.c.close();
 console.log(`${width}: copy fallback (real clipboard) and manual link box pass; zero page/console errors, zero writes`);
}}finally{await browser.close();}
console.log('Share loop accepted on '+base);
