// First AI edit over the game, against `python qa/local.py --lightweight-game --included-beta`.
// Synthetic provider only: no model call, no real allowance. Fresh anonymous contexts at 375 and 1440.
// Usage: PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node qa/check-first-edit.mjs http://127.0.0.1:PORT
import assert from 'node:assert/strict';import {mkdir} from 'node:fs/promises';import {pathToFileURL} from 'node:url';
const base=process.argv[2];assert.equal(new URL(base).hostname,'127.0.0.1');
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);await mkdir('qa/first-edit',{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const phone={viewport:{width:375,height:812},isMobile:true,hasTouch:true},desktop={viewport:{width:1440,height:900}};
async function fresh(options,setup){
 const c=await browser.newContext(options),errors=[],posts=[],external=[];let hold=null,fail=null;
 await c.addInitScript(setup=>{if(window!==top)return;localStorage.setItem('openworld.analytics.v1','off');for(const [k,v] of Object.entries(setup||{}))localStorage.setItem(k,v);},setup);
 await c.route('**/*',async route=>{const r=route.request(),u=new URL(r.url());if(u.origin!==base){external.push(u.hostname);return route.abort();}
  if(r.method()==='POST'&&u.pathname.startsWith('/api/')){posts.push({path:u.pathname,body:r.postData()?JSON.parse(r.postData()):null});
   if(u.pathname.startsWith('/api/chat')&&fail){const f=fail;fail=null;return route.fulfill({status:503,json:f});}
   if(u.pathname.startsWith('/api/chat')&&hold){const h=hold;hold=null;return h(route);}}
  return route.continue();});
 const p=await c.newPage();p.setDefaultTimeout(20000);p.on('pageerror',e=>errors.push(e.message));
 return {c,p,errors,posts,external,holdNext(){return new Promise(resolve=>{hold=route=>resolve(route)})},failNext(json){fail=json}};
}
const card=p=>p.locator('#ow-ideas-card'),pill=p=>p.locator('#ow-ideas-pill');
async function noOverflow(p,label){
 assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,label+' horizontal overflow');
 const box=await card(p).boundingBox(),vw=p.viewportSize().width,vh=p.viewportSize().height;
 assert.ok(box.x>=0&&box.y>=0&&box.x+box.width<=vw&&box.y+box.height<=vh,label+' card inside viewport '+JSON.stringify(box));
 for(const b of await card(p).locator('button:visible').all()){const r=await b.boundingBox();assert.ok(r.height>=44&&r.width>=44,label+' 44px target '+(await b.textContent()));}
}
try{for(const [width,options] of [[375,phone],[1440,desktop]]){
 const t=await fresh(options),p=t.p;const shot=name=>p.screenshot({path:`qa/first-edit/${name}-${width}.png`});
 await p.goto(base+'/');await card(p).waitFor();
 assert.equal(await p.locator('#ow-ideas-title').textContent(),'Change this game with words');
 assert.equal(await p.locator('#ow-ideas-left').textContent(),'2 free AI edits left');
 const chips=await p.locator('#ow-ideas-list button').allTextContents();
 assert.deepEqual(chips.map(x=>x.split(' ').slice(1).join(' ')),['Make it snow','Turn the sky purple','Add a dragon','Write your own']);
 const panelOpen=await p.locator('#ow-panel.ow-open').count();assert.equal(panelOpen,width===1440?1:0);
 if(width===1440){const box=await card(p).boundingBox();assert.ok(box.x+box.width<=1440-300,'desktop card stays over the game, left of the editor');}
 else{const box=await card(p).boundingBox();assert.ok(box.y>812/2,'phone card sits low, within thumb reach');}
 await noOverflow(p,width+' ideas');await shot('ideas');
 // Hide folds it into a small button that keeps the count; the choice survives a reload.
 await p.locator('#ow-ideas-hide').click();await pill(p).waitFor();assert.equal(await card(p).isVisible(),false);
 assert.equal((await pill(p).textContent()).trim().split(' ').slice(1).join(' '),'2 free AI edits left');await shot('collapsed');
 await p.reload();await pill(p).waitFor();assert.equal(await card(p).isVisible(),false);await pill(p).click();await card(p).waitFor();
 if(width===1440){// Clicking into the game to play folds the card away.
  await p.mouse.click(300,700);await pill(p).waitFor();await pill(p).click();await card(p).waitFor();}
 // One click: the idea fills and submits the normal included edit, with visible progress.
 const pending=t.holdNext();await p.locator('#ow-ideas-list button',{hasText:'Make it snow'}).click();const route=await pending;
 const sent=t.posts.at(-1);assert.equal(sent.path,'/api/chat/idea');assert.equal(sent.body.funding,'included');assert.equal(sent.body.api_key,undefined);
 assert.match(sent.body.message,/^Make it snow: /);assert.match(sent.body.request_id,/^[0-9a-f-]{36}$/);
 assert.equal(await p.locator('#ow-ideas-title').textContent(),'Claude is editing your game');
 await p.locator('#ow-ideas-time',{hasText:'0:01'}).waitFor();
 assert.match(await p.locator('#ow-ideas-stage').textContent(),/Claude/);
 assert.ok(parseFloat(await p.locator('#ow-ideas-bar').evaluate(e=>e.style.width))>0);
 assert.equal(await p.locator('#ow-ideas-list').isVisible(),false);await noOverflow(p,width+' working');await shot('working');
 await route.continue();
 // Success opens the private version and asks to share it.
 await p.waitForURL(/\/v\/[0-9a-f-]{36}$/);await p.locator('#ow-ideas-title',{hasText:'Your version is ready'}).waitFor();
 await p.locator('#ow-ideas-left',{hasText:'1 free AI edit left'}).waitFor();
 assert.equal(await p.locator('#ow-ideas-share').textContent(),'Share your version');assert.equal(await p.locator('#ow-ideas-more').isVisible(),true);
 await noOverflow(p,width+' ready');await shot('ready');
 await p.locator('#ow-ideas-share').click();await p.locator('#ow-share-modal.ow-show').waitFor();
 assert.equal(t.posts.at(-1).path,'/api/versions/share');assert.match(await p.locator('#ow-share-link').inputValue(),/\/shared\/[A-Za-z0-9_-]+$/);
 await shot('shared');await p.locator('#ow-share-close').click();
 // The share prompt is done after sharing; a reload shows no ideas to a now-returning editor.
 await p.reload();await p.locator('#ow-included-status',{hasText:'1 included attempts'}).waitFor({state:'attached'});await p.waitForTimeout(300);
 assert.equal(await p.locator('#ow-ideas').isVisible(),false);
 assert.deepEqual(t.errors,[]);assert.deepEqual(t.external,[]);await t.c.close();
}
 // Phone: a failure keeps the draft and says why; ideas remain while edits are left; the last edit says none remain.
 {const t=await fresh(phone),p=t.p;await p.goto(base+'/');await card(p).waitFor();
  t.failNext({detail:'Shared beta budget is paused. Play stays free.',code:'budget_paused',dispatched:false});
  await p.locator('#ow-ideas-list button',{hasText:'Add a dragon'}).click();
  await p.locator('#ow-ideas-title',{hasText:'That edit did not finish'}).waitFor();
  assert.equal(await p.locator('#ow-ideas-sub').textContent(),'Shared beta budget is paused. Play stays free.');
  assert.equal(await p.locator('#ow-ideas-list button').count(),4);await noOverflow(p,'375 failed');await p.screenshot({path:'qa/first-edit/failed-375.png'});
  await p.locator('#ow-ideas-list button',{hasText:'Write your own'}).click();await p.locator('#ow-panel.ow-open').waitFor();
  assert.match(await p.locator('#ow-input').inputValue(),/^Add a big friendly dragon /);await p.locator('#ow-panel-close').click();
  // Typed edits keep the original path.
  t.failNext({detail:'Synthetic typed failure.',dispatched:false});await p.locator('#ow-fab').click();await p.locator('#ow-input').fill('A small typed change');
  await p.getByRole('button',{name:'Send game change',exact:true}).click();await p.locator('#ow-messages',{hasText:'Synthetic typed failure.'}).waitFor();
  assert.equal(t.posts.at(-1).path,'/api/chat');await p.locator('#ow-panel-close').click();
  await p.locator('#ow-ideas-list button',{hasText:'Turn the sky purple'}).click();await p.waitForURL(/\/v\//);
  await p.locator('#ow-ideas-title',{hasText:'Your version is ready'}).waitFor();await p.locator('#ow-ideas-left',{hasText:'1 free AI edit left'}).waitFor();
  const before=p.url();await p.locator('#ow-ideas-more').click();await p.locator('#ow-ideas-list button',{hasText:'Make it snow'}).click();await p.waitForURL(u=>u.href!==before);
  await p.locator('#ow-ideas-left',{hasText:'No free AI edits left right now'}).waitFor();
  assert.equal(await p.locator('#ow-ideas-more').isVisible(),false);assert.match(await p.locator('#ow-ideas-note').textContent(),/come back 24 hours after use/);
  await noOverflow(p,'375 none left');await p.screenshot({path:'qa/first-edit/none-left-375.png'});
  assert.deepEqual(t.errors,[]);assert.deepEqual(t.external,[]);await t.c.close();}
 // Returning editors and own-key mode never see the ideas card.
 for(const setup of [{ow_session_id:'00000000-0000-4000-8000-000000000000'},{ow_ai_funding:'byok'}]){
  const t=await fresh(desktop,setup),p=t.p;await p.goto(base+'/');await p.locator('#ow-included-status').filter({hasText:/attempts|Anthropic/}).waitFor();await p.waitForTimeout(300);
  assert.equal(await p.locator('#ow-ideas').isVisible(),false,JSON.stringify(setup));await t.c.close();}
 console.log('375/1440: ideas over the game with the plain free-edit count, hide/restore, one-click included edit on /api/chat/idea with live progress, private version, share prompt and link, failure detail with ideas kept, typed edits on /api/chat, none-left copy, no card for returning or own-key editors; no overflow, 44px targets, no page errors or external requests.');
}finally{await browser.close();}
