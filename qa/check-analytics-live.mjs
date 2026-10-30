// Actual public-site analytics acceptance. No provider response is intercepted.
// Run only after the coordinator confirms the Betterloop SDK/server is released.
import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const entry=process.argv[2]; if(!entry)throw Error('Pass the installed Playwright module entry');
const {chromium}=await import(pathToFileURL(entry).href);
const origin='https://open-world.gg', sentinel='private-analytics-sentinel';
const config=JSON.parse(await readFile('/Users/nirfeinstein/Documents/ChatGPT/almost finished projects + marketing/.runtime/analytics-public-config.json','utf8'));
const expected=config.OpenWorld, lines=[];
const paths=new Set(['/','/privacy','/index','/index.html','/privacy.html']);
const collection=url=>{
 const u=new URL(url);
 if(/google-analytics\.com$/.test(u.hostname)&&/\/collect$/.test(u.pathname))return 'Google';
 if(u.hostname==='api.mixpanel.com'&&u.pathname==='/track')return 'Mixpanel';
 if(u.hostname==='betterloopai.com'&&u.pathname==='/api/ingest')return 'Betterloop';
 return null;
};
const asset=url=>{const u=new URL(url);return u.hostname==='www.googletagmanager.com'||u.hostname==='betterloopai.com'&&u.pathname==='/sdk.js';};
function validate(request){
 const kind=collection(request.url()), body=request.postData()||'';
 assert.ok(!request.url().includes(sentinel)&&!body.includes(sentinel),'Private query/hash reached analytics');
 let events=[];
 if(kind==='Google'){
  const q=new URLSearchParams(new URL(request.url()).search),posted=new URLSearchParams(body),get=key=>posted.get(key)||q.get(key);
  assert.equal(get('tid'),expected.gaId);
  if(get('dl')){const u=new URL(get('dl'));assert.equal(u.origin,origin);assert.ok(paths.has(u.pathname));assert.equal(u.search,'');assert.equal(u.hash,'');}
  events=[get('en')];
 }else if(kind==='Mixpanel'){
  const item=JSON.parse(new URLSearchParams(body).get('data'));
  assert.equal(item.properties.token,expected.mixpanelToken);assert.equal(item.properties.product,'OpenWorld');assert.ok(paths.has(item.properties.path));
  assert.deepEqual(Object.keys(item.properties).sort(),['token','distinct_id','product','path','$insert_id','time'].sort());
  events=[item.event];
 }else if(kind==='Betterloop'){
  const item=JSON.parse(body);assert.equal(item.key,config.Betterloop.betterloopKey);assert.equal(item.url,origin);assert.equal(item.text,false);
  assert.ok(item.events.length>0);
  for(const event of item.events){assert.ok(paths.has(event.path));if(event.attrs)assert.ok(!JSON.stringify(event.attrs).includes(sentinel));}
  events=item.events.map(event=>event.t==='custom'?event.attrs?.name:event.t);
 }
 return {kind,events};
}
async function openChoices(page){
 const button=page.locator('[data-analytics-open]').last();
 if(!await button.isVisible())await page.locator('#ow-fab').click();
 await button.click();await page.getByRole('dialog',{name:'Optional website analytics',exact:true}).waitFor();
}
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try{
 for(const width of [375,1440]){
  const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),requests=[],receipts=[],failures=[],errors=[];
  context.on('request',request=>{if(collection(request.url())){try{requests.push(validate(request));}catch(error){failures.push(error.message);}}else if(asset(request.url()))requests.push({kind:'SDK',events:[]});});
  context.on('response',async response=>{const kind=collection(response.url());if(kind){const item={kind,status:response.status()};try{if(kind!=='Google')item.body=(await response.text()).slice(0,200);}catch{}receipts.push(item);}});
  const page=await context.newPage();page.setDefaultTimeout(30_000);page.setDefaultNavigationTimeout(120_000);page.on('pageerror',error=>errors.push(error.message));
  await page.goto(`${origin}/?private=${sentinel}#${sentinel}`,{waitUntil:'domcontentloaded'});
  await page.locator('[data-analytics-open]').waitFor({state:'attached'});
  await page.waitForTimeout(1000);assert.equal(requests.length,0,'No analytics assets or collection before choice');
  await openChoices(page);const dialog=page.getByRole('dialog',{name:'Optional website analytics',exact:true});
  await page.screenshot({path:`qa/analytics-live-${width}.jpg`,type:'jpeg',quality:75});
  await dialog.getByRole('button',{name:'Allow analytics',exact:true}).click();
  await page.waitForFunction(()=>window.Betterloop&&window.dataLayer?.some(args=>args[0]==='event'&&args[1]==='page_view'));
  await page.locator('#ow-vdrop-btn').click();
  await page.locator('#ow-store-modal').waitFor({state:'visible'});
  await page.waitForTimeout(7000);
  assert.ok(receipts.some(item=>item.kind==='Google'&&item.status>=200&&item.status<300),'Google successful receipt missing');
  assert.ok(receipts.some(item=>item.kind==='Mixpanel'&&item.status===200&&item.body==='1'),'Mixpanel successful receipt missing');
  assert.ok(receipts.some(item=>item.kind==='Betterloop'&&item.status===200&&item.body.includes('"ok":true')),'Betterloop successful receipt missing');
  for(const kind of ['Google','Mixpanel','Betterloop'])assert.ok(requests.some(item=>item.kind===kind&&item.events.includes('store_opened')),kind+' fixed Store action missing');
  await page.locator('#ow-store-close').click();await openChoices(page);await dialog.getByRole('button',{name:'Keep analytics off',exact:true}).click();
  assert.equal(await page.evaluate(()=>localStorage.getItem('openworld.analytics.v1.device')),null);
  assert.equal(await page.evaluate(()=>sessionStorage.getItem('_fp_sid')),null);
  const before=requests.length;
  await page.locator('#ow-vdrop-btn').click();await page.locator('#ow-store-close').click();await page.waitForTimeout(800);
  assert.equal(requests.length,before,'Withdrawal stops new collection');
  await page.goto(origin+'/privacy',{waitUntil:'domcontentloaded'});await page.locator('[data-analytics-open]').waitFor();await page.waitForTimeout(800);assert.equal(requests.length,before,'Off choice survives navigation');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  await page.evaluate(()=>localStorage.setItem('openworld.analytics.v1','allowed'));
  for(const route of ['/account','/contact']){await page.goto(origin+route+'?private='+sentinel,{waitUntil:'domcontentloaded'});await page.waitForTimeout(800);assert.equal(requests.length,before,route+' stays untracked even with saved allow');}
  assert.deepEqual(failures,[]);assert.deepEqual(errors,[]);
  lines.push(`${width}: no analytics before choice; genuine Google2xx/Mixpanel1/Betterloop200 accepted; real Store click emitted fixed store_opened to all3; sensitive query/hash absent; withdrawal removed identifiers and stayed quiet after navigation; account/contact with saved allow stayed quiet; no page errors or policy-page overflow.`);
  await context.close();
 }
 const context=await browser.newContext({viewport:{width:375,height:900},serviceWorkers:'block'});let sent=0;
 context.on('request',request=>{if(collection(request.url())||asset(request.url()))sent++;});
 await context.addInitScript(()=>{localStorage.setItem('openworld.analytics.v1','allowed');Object.defineProperty(navigator,'globalPrivacyControl',{value:true});});
 const page=await context.newPage();await page.goto(origin+'/privacy',{waitUntil:'domcontentloaded'});await page.getByText('Optional analytics is off because this browser requests privacy.').waitFor();await page.waitForTimeout(1000);assert.equal(sent,0);await context.close();
 lines.push('GPC overrides saved allow on the actual public policy page;0 analytics requests. Provider HTTP acceptance is proved; dashboard visibility is recorded separately by the coordinator. No generation, signup, message or paid transaction.');
 await writeFile('qa/analytics-live.log',lines.join('\n')+'\n');console.log(lines.join('\n'));
}finally{await browser.close();}
