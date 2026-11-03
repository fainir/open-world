// After a successful AI edit, "Share your version" uses the same one-tap share as the shared page.
// Against `python qa/local.py --lightweight-game --included-beta` (synthetic provider, no model call).
// The share sheet cannot open in headless Chrome, so it is replaced by a recorder; copy uses the real clipboard.
// Usage: node qa/check-share-prompt.mjs http://127.0.0.1:PORT <playwright/index.mjs> [out-dir]
import assert from 'node:assert/strict';import {mkdir} from 'node:fs/promises';import {pathToFileURL} from 'node:url';
const base=process.argv[2];assert.equal(new URL(base).hostname,'127.0.0.1');const out=process.argv[4]||'qa/share-loop';
const {chromium}=await import(pathToFileURL(process.argv[3]).href);await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const runs=[[375,'sheet',{viewport:{width:375,height:812},isMobile:true,hasTouch:true}],[1440,'copy',{viewport:{width:1440,height:900}}]];
try{for(const [width,mode,options] of runs){
 const c=await browser.newContext({...options,permissions:mode==='copy'?['clipboard-read','clipboard-write']:[]}),errors=[],external=[];
 await c.addInitScript(mode=>{if(window!==top)return;localStorage.setItem('openworld.analytics.v1','off');window.__shares=[];
  Object.defineProperty(Navigator.prototype,'share',{configurable:true,value:mode==='sheet'?async data=>{window.__shares.push(data)}:undefined});},mode);
 await c.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin!==base){external.push(u.hostname);return route.abort();}return route.continue();});
 const p=await c.newPage();p.setDefaultTimeout(30000);p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
 await p.goto(base+'/');await p.locator('#ow-ideas-card').waitFor();
 await p.locator('#ow-ideas-list button',{hasText:'Make it snow'}).click();await p.waitForURL(/\/v\/[0-9a-f-]{36}$/);
 await p.locator('#ow-ideas-title',{hasText:'Your version is ready'}).waitFor();
 const shared=p.waitForResponse(r=>r.url().endsWith('/api/versions/share'));await p.locator('#ow-ideas-share').click();
 const slug=(await (await shared).json()).share_slug,link=base+'/shared/'+slug;
 if(mode==='sheet'){
  await p.waitForFunction(()=>window.__shares.length===1);const sent=await p.evaluate(()=>window.__shares[0]);
  assert.equal(sent.url,link);assert.equal(sent.title,'My OpenWorld game');assert.match(sent.text,/OpenWorld/);
  await p.locator('#ow-toast.ow-show',{hasText:'Thanks for sharing!'}).waitFor();
  assert.equal(await p.locator('#ow-share-modal.ow-show').count(),0,'no dialog when the share sheet worked');
 }else{
  await p.locator('#ow-share-modal.ow-show').waitFor();assert.equal(await p.locator('#ow-share-link').inputValue(),link);
  assert.equal(await p.locator('#ow-share-copied').textContent(),'Link copied. Paste it anywhere.');
  assert.equal(await p.evaluate(()=>navigator.clipboard.readText()),link);
  assert.equal(await p.locator('#ow-share-native').isVisible(),false,'no Share button without a share sheet');
 }
 await p.screenshot({path:`${out}/share-prompt-${width}.jpg`,type:'jpeg',quality:75});
 // The shared link it hands out opens the shared page with its bar.
 await p.goto(link);await p.getByRole('link',{name:'Remix this'}).waitFor();
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);await c.close();
 console.log(`${width}: share prompt after a synthetic AI edit -> ${mode==='sheet'?'share sheet':'copied link in the dialog'} (${link}); shared page opens; no errors`);
}}finally{await browser.close();}
