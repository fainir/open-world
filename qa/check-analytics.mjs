// Owned-site UI only. All analytics destinations receive synthetic local mocks.
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
const [base,entry]=process.argv.slice(2);
assert.equal(new URL(base).hostname,'127.0.0.1');
const {chromium}=await import(pathToFileURL(entry).href);
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const config="window.SiteAnalyticsConfig={gaId:'G-SYNTHETIC',mixpanelToken:'"+'a'.repeat(32)+"',betterloopKey:'bl_synthetic_public_key'};";
const sdk="window.__sdkCalls=[];window.Betterloop={init:o=>__sdkCalls.push(['init',o]),shutdown:o=>__sdkCalls.push(['shutdown',o]),track:e=>__sdkCalls.push(['track',e])};";
async function fixture(width,options={}) {
 const context=await browser.newContext({viewport:{width,height:900}}),requests=[];let delayed;
 await context.route('**/*',async route=>{
  const u=new URL(route.request().url());
  if(u.pathname.endsWith('/analytics-config.js'))return route.fulfill({contentType:'text/javascript',body:config});
  if(u.hostname==='www.googletagmanager.com') {requests.push(['google']);return route.fulfill({contentType:'text/javascript',body:'window.__googleLoaded=true;'});}
  if(u.hostname==='api.mixpanel.com') {requests.push(['mixpanel',route.request().postData()]);return route.fulfill({contentType:'text/plain',headers:{'Access-Control-Allow-Origin':'*'},body:'1'});}
  if(u.hostname==='betterloopai.com') {requests.push(['betterloop']);if(options.delay)await new Promise(resolve=>{delayed=()=>resolve();});return route.fulfill({contentType:'text/javascript',body:sdk});}
  if(u.origin===base||['cdn.jsdelivr.net','api.country.is','open.er-api.com','api.exchangerate-api.com'].includes(u.hostname))return route.continue();
  return route.abort();
 });
 if(options.blocked)await context.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw Error('Synthetic storage unavailable');}}));
 if(options.gpc)await context.addInitScript(()=>Object.defineProperty(navigator,'globalPrivacyControl',{get:()=>true}));
 if(options.dnt)await context.addInitScript(()=>Object.defineProperty(navigator,'doNotTrack',{get:()=> '1'}));
 const page=await context.newPage(),errors=[];page.setDefaultTimeout(20000);console.log('Fixture browser ready',width,options);page.on('pageerror',e=>errors.push(e.message));
 // Isolate analytics storage failure on the public policy page; the studio itself requires local storage.
 await page.goto(base+(options.blocked?'/privacy':'/')+'?private=sentinel-DO-NOT-SEND#secret-sentinel',{waitUntil:'domcontentloaded',timeout:120000});console.log('Fixture page ready',width,options);
 return {context,page,requests,errors,release:()=>delayed?.()};
}
async function open(page){const button=page.locator('[data-analytics-open]').last();if(!await button.isVisible()){const editor=page.locator('#ow-fab');if(await editor.count())await editor.click();}await button.click();await page.getByRole('dialog',{name:'Optional website analytics',exact:true}).waitFor();}
try {
 for(const width of [375,1440]) {
  const f=await fixture(width);assert.equal(f.requests.length,0);assert.equal(await f.page.evaluate(()=>Object.keys(localStorage).some(k=>k.endsWith('.device'))),false);
  await open(f.page);const dialog=f.page.getByRole('dialog',{name:'Optional website analytics',exact:true});
  assert.equal(await dialog.getByRole('button',{name:'Keep analytics off',exact:true}).evaluate(el=>el===document.activeElement),true);
  for(let i=0;i<10;i++){await f.page.keyboard.press('Tab');assert.equal(await dialog.evaluate(el=>el.contains(document.activeElement)),true);}
  assert.equal(await dialog.evaluate(el=>el.scrollWidth<=innerWidth),true);
  await f.page.screenshot({path:'qa/analytics-choices-'+width+'.jpg',type:'jpeg',quality:75});
  await dialog.getByRole('button',{name:'Allow analytics',exact:true}).click();console.log('Allowed at width',width,JSON.stringify(await f.page.evaluate(()=>({ga:window.__googleLoaded,sdk:window.__sdkCalls,choice:localStorage.getItem('openworld.analytics.v1'),scripts:Array.from(document.scripts).map(s=>s.src)}))));
  await f.page.waitForFunction(()=>window.__sdkCalls?.some(c=>c[0]==='init')&&window.__googleLoaded);
  await f.page.waitForFunction(()=>window.SiteAnalytics!=null);
  const event=await f.page.evaluate(()=>{const e=window.GramfixAnalytics?'download_button_clicked':document.title.includes('Small Living')?'enquiry_opened':'store_opened';window.SiteAnalytics.track(e,{prompt:'sentinel-DO-NOT-SEND'});return e;});
  await f.page.waitForFunction(e=>window.__sdkCalls.some(c=>c[0]==='track'&&c[1]===e),event);
  assert.ok(!/sentinel/.test(JSON.stringify(f.requests)));
  const queued=await f.page.evaluate(()=>JSON.stringify(window.dataLayer));assert.ok(!/sentinel/.test(queued));
  assert.equal(await f.page.evaluate(()=>window.dataLayer.filter(c=>c[0]==='event'&&c[1]==='page_view').length),1);
  const mix=f.requests.filter(r=>r[0]==='mixpanel');assert.ok(mix.length>=1);for(const [,body] of mix){const p=new URLSearchParams(body);assert.equal(p.get('ip'),'0');assert.equal(JSON.parse(p.get('data')).properties.path,'/');}
  await open(f.page);await f.page.getByRole('button',{name:'Keep analytics off',exact:true}).click();
  assert.equal(await f.page.evaluate(()=>window['ga-disable-G-SYNTHETIC']),true);
  assert.equal(await f.page.evaluate(()=>Object.keys(localStorage).some(k=>k.endsWith('.device'))),false);
  assert.equal(await f.page.evaluate(()=>window.__sdkCalls.at(-1)[1].discard),true);
  const before=f.requests.length;await f.page.evaluate(e=>window.SiteAnalytics.track(e),event);assert.equal(f.requests.length,before);
  await f.page.reload();assert.equal(f.requests.length,before);
  assert.deepEqual(f.errors,[]);await f.context.close();console.log(width+': actual consent/focus/fit; all3 mock providers; fixed sanitized event; one pageview; withdrawal/identifier cleanup/reload pass');
 }
 for(const options of [{blocked:true},{gpc:true},{dnt:true}]) {
  const f=await fixture(375,options);await open(f.page);await f.page.getByRole('button',{name:'Allow analytics',exact:true}).click();assert.equal(f.requests.length,0);
  if(options.blocked)await f.page.getByRole('status').filter({hasText:'Analytics remains off'}).waitFor();
  assert.deepEqual(f.errors,[]);await f.context.close();console.log(JSON.stringify(options)+': no provider requests');
 }
 const race=await fixture(375,{delay:true});await open(race.page);await race.page.getByRole('button',{name:'Allow analytics',exact:true}).click();
 await race.page.waitForFunction(()=>Array.from(document.scripts).some(s=>s.src==='https://betterloopai.com/sdk.js?v=20261030'));
 await open(race.page);await race.page.getByRole('button',{name:'Keep analytics off',exact:true}).click();race.release();
 await race.page.waitForFunction(()=>window.__sdkCalls!=null);assert.equal(await race.page.evaluate(()=>window.__sdkCalls.some(c=>c[0]==='init')),false);assert.deepEqual(race.errors,[]);await race.context.close();console.log('Delayed SDK withdrawal: no later initialization');
 const failed=await fixture(375,{delay:true});await open(failed.page);await failed.page.getByRole('button',{name:'Allow analytics',exact:true}).click();
 await failed.page.waitForFunction(()=>Array.from(document.scripts).some(s=>s.src==='https://betterloopai.com/sdk.js?v=20261030'));
 await failed.page.evaluate(()=>{const write=Storage.prototype.setItem;window.__writesBlocked=true;Storage.prototype.setItem=function(k,v){if(window.__writesBlocked)throw Error('Synthetic write unavailable');return write.call(this,k,v);};});
 await open(failed.page);await failed.page.getByRole('button',{name:'Keep analytics off',exact:true}).click();
 await failed.page.getByRole('status').filter({hasText:'Analytics remains off'}).waitFor();failed.release();
 await failed.page.waitForFunction(()=>window.__sdkCalls!=null);const requestsBefore=failed.requests.length;
 await failed.page.evaluate(()=>{window.dispatchEvent(new Event('pageshow'));window.dispatchEvent(new Event('focus'));window.SiteAnalytics.track('store_opened');});
 assert.equal(await failed.page.evaluate(()=>window.__sdkCalls.some(c=>c[0]==='init')),false);assert.equal(failed.requests.length,requestsBefore);assert.equal(await failed.page.evaluate(()=>window['ga-disable-G-SYNTHETIC']),true);
 await failed.page.evaluate(()=>window.__writesBlocked=false);await failed.page.getByRole('button',{name:'Allow analytics',exact:true}).click();
 await failed.page.waitForFunction(()=>window.__sdkCalls.some(c=>c[0]==='init'));assert.deepEqual(failed.errors,[]);await failed.context.close();console.log('Failed withdrawal remains off across late SDK/focus/pageshow; successful fresh choice restores optional tracking');
} finally {await browser.close();}
