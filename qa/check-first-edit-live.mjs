// Read-only public check of the first-edit card on https://open-world.gg. Never clicks an idea,
// so it cannot dispatch a model call or spend an included edit. Fresh anonymous contexts.
// Usage: PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node qa/check-first-edit-live.mjs
import assert from 'node:assert/strict';import {mkdir} from 'node:fs/promises';import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);await mkdir('qa/first-edit',{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
try{for(const [width,options] of [[375,{viewport:{width:375,height:812},isMobile:true,hasTouch:true}],[1440,{viewport:{width:1440,height:900}}]]){
 const c=await browser.newContext(options),p=await c.newPage(),errors=[],chats=[];p.setDefaultTimeout(30000);
 await c.addInitScript(()=>{if(window===top)localStorage.setItem('openworld.analytics.v1','off')});
 p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/chat'))chats.push(r.url())});
 await p.goto('https://open-world.gg/',{waitUntil:'domcontentloaded'});
 const card=p.locator('#ow-ideas-card');await card.waitFor();
 assert.equal(await p.locator('#ow-ideas-title').textContent(),'Change this game with words');
 const left=await p.locator('#ow-ideas-left').textContent();assert.match(left,/^[12] free AI edits? left$/);
 const chips=(await p.locator('#ow-ideas-list button').allTextContents()).map(x=>x.split(' ').slice(1).join(' '));
 assert.deepEqual(chips,['Make it snow','Turn the sky purple','Add a dragon','Write your own']);
 assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 const box=await card.boundingBox();assert.ok(box.x>=0&&box.y>=0&&box.x+box.width<=width&&box.y+box.height<=options.viewport.height);
 if(width===1440)assert.ok(box.x+box.width<=1440-300,'card stays over the game, left of the open editor');
 for(const b of await card.locator('button:visible').all()){const r=await b.boundingBox();assert.ok(r.height>=44&&r.width>=44)}
 await p.waitForTimeout(6000);await p.screenshot({path:`qa/first-edit/live-ideas-${width}.png`});
 if(width===1440){await p.mouse.click(400,700);await p.locator('#ow-ideas-pill').waitFor();assert.equal(await card.isVisible(),false);await p.screenshot({path:'qa/first-edit/live-playing-1440.png'});}
 assert.deepEqual(chats,[]);assert.deepEqual(errors,[]);
 console.log(`${width}px live: ideas card over the real game, "${left}", 3 ideas + Write your own, inside the viewport, 44px targets, no overflow${width===1440?', folds when the game takes focus':''}, no edit request, no page errors.`);
 await c.close();
}}finally{await browser.close();}
