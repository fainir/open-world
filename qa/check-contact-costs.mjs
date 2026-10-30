import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const base=process.argv[2],live=process.argv.includes('--public');assert.ok(base);if(!live)assert.equal(new URL(base).hostname,'127.0.0.1');
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
await mkdir('qa/contact-costs',{recursive:true});const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
try{for(const width of[375,1440]){
 const context=await browser.newContext({viewport:{width,height:900}}),attempts=[],external=[],errors=[];let mode='failed',retryMode='failed';
 await context.addInitScript(()=>{if(window!==top)return;localStorage.setItem('openworld.analytics.v1','allowed');Object.defineProperty(navigator,'doNotTrack',{value:'1'});localStorage.setItem('ow_token','synthetic-browser-identity-only');localStorage.setItem('ow_user',JSON.stringify({username:'Synthetic admin'}));});
 const contacts=['legacy','queued','retry','accepted','review'].map((status,i)=>({id:'synthetic-'+i,name:'Synthetic '+status,email:'synthetic@example.test',message:'Synthetic private inbox '+status,is_read:false,notification_status:status,notification_attempts:status==='legacy'?0:1,notification_error:status==='review'?'delivery_uncertain':null,notification_reference:status==='accepted'?'synthetic-reference':null}));
 await context.route('**/*',async route=>{
  const r=route.request(),u=new URL(r.url());if(u.origin!==base){external.push(u.hostname);return route.abort();}
  if(live&&u.pathname==='/game/base')return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="en"><title>Functional UI fixture</title><body>Game execution is outside this changed-screen check.</body></html>'});
  if(u.pathname==='/api/contact'){
   const b=JSON.parse(r.postData());attempts.push({key:r.headers()['idempotency-key'],body:b});assert.equal(r.method(),'POST');assert.equal(r.headers().authorization,undefined);
   if(mode==='network')return route.abort('timedout');
   return route.fulfill({status:mode==='accepted'?200:mode==='limited'?429:503,json:mode==='accepted'?{status:'stored',notification:'queued'}:{detail:'synthetic failure'}});
  }
  if(u.pathname==='/api/admin/contacts')return route.fulfill({json:contacts});
  if(u.pathname==='/api/admin/all-versions')return route.fulfill({json:[]});
  if(u.pathname.endsWith('/retry'))return route.fulfill({status:retryMode==='accepted'?200:503,json:{status:'queued'}});
  if(u.pathname==='/api/auth/me')return route.fulfill({json:{id:'synthetic-user',username:'Synthetic admin',is_admin:true}});
  if(u.pathname.startsWith('/api/')&&r.method()==='GET')return route.fulfill({json:[]});
  if(r.method()!=='GET'&&r.method()!=='HEAD')throw Error('Unexpected write blocked: '+u.pathname);
  return route.continue();
 });
 const page=await context.newPage();page.setDefaultTimeout(20000);page.on('pageerror',e=>errors.push(e.message));
 const fits=async()=>{assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);};
 await page.goto(base+'/contact');const form=page.locator('#contact-form'),button=page.locator('#submit-btn');await button.waitFor();await assert.doesNotReject(()=>button.waitFor({state:'visible'}));
 const fill=async()=>{await page.getByLabel('Name',{exact:true}).fill('Synthetic');await page.getByLabel('Email',{exact:true}).fill('synthetic@example.test');await page.getByLabel('Message',{exact:true}).fill('Synthetic contact QA');};
 await button.click();assert.equal(attempts.length,0);await fill();await button.click();await page.getByRole('alert').filter({hasText:'could not confirm'}).waitFor();const key=attempts.at(-1).key;assert.match(key,/^[a-f0-9-]{36}$/i);assert.equal(await page.getByLabel('Message',{exact:true}).inputValue(),'Synthetic contact QA');
 mode='limited';await button.click();await page.getByRole('alert').filter({hasText:'Please wait'}).waitFor();assert.equal(attempts.at(-1).key,key);
 mode='network';await button.click();await page.getByRole('alert').waitFor();assert.equal(attempts.at(-1).key,key);
 mode='accepted';await button.click();await page.getByRole('status').filter({hasText:'Saved for the operator'}).waitFor();assert.equal(attempts.at(-1).key,key);assert.equal(await page.getByLabel('Message',{exact:true}).inputValue(),'');
 await fill();await button.click();await page.getByRole('status').filter({hasText:'Saved for the operator'}).waitFor();assert.notEqual(attempts.at(-1).key,key);assert.ok(!(await page.getByRole('status').innerText()).includes('has been sent'));
 const before=attempts.length;await fill();await page.evaluate(()=>Object.defineProperty(crypto,'randomUUID',{value:undefined,configurable:true}));await button.click();await page.getByRole('alert').filter({hasText:'cannot send securely'}).waitFor();assert.equal(attempts.length,before);assert.equal(new URL(page.url()).search,'');await fits();
 for(const control of await form.locator('input:not([name=website]),textarea,button').all()){const b=await control.boundingBox();assert.ok(b.width>=44&&b.height>=44);}
 const contrast=await page.evaluate(()=>{
  const rgb=value=>value.match(/[\d.]+/g).map(Number),luma=values=>values.slice(0,3).map(n=>n/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4).reduce((sum,n,i)=>sum+n*[.2126,.7152,.0722][i],0);
  const base=rgb(getComputedStyle(document.body).backgroundColor),ratio=(foreground,background)=>{const a=luma(foreground),b=luma(background);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);};
  const error=getComputedStyle(document.getElementById('error-msg')),layer=rgb(error.backgroundColor),background=layer.slice(0,3).map((n,i)=>n*(layer[3]??1)+base[i]*(1-(layer[3]??1)));
  const button=getComputedStyle(document.getElementById('submit-btn'));
  return {links:[...document.querySelectorAll('a')].filter(a=>a.getClientRects().length).map(a=>ratio(rgb(getComputedStyle(a).color),base)),error:ratio(rgb(error.color),background),button:ratio(rgb(button.color),rgb(button.backgroundColor))};
 });assert.ok(contrast.links.every(n=>n>=4.5));assert.ok(contrast.error>=4.5);assert.ok(contrast.button>=4.5);
 assert.match(await form.getAttribute('method'),/post/i);assert.equal(await page.getByRole('link',{name:'fainir2006@gmail.com',exact:true}).getAttribute('href'),'mailto:fainir2006@gmail.com');
 await page.screenshot({path:'qa/contact-costs/'+(live?'public-':'')+'contact-'+width+'.jpg',type:'jpeg',quality:70,fullPage:true});
 await page.goto(base+'/terms');await page.getByRole('heading',{name:'Terms & current costs',exact:true}).waitFor();for(const t of['Free:','Bring your own key:','Paid plan:'])assert.ok((await page.locator('main').innerText()).includes(t));await fits();await page.screenshot({path:'qa/contact-costs/'+(live?'public-':'')+'terms-'+width+'.jpg',type:'jpeg',quality:65,fullPage:true});
 await page.goto(base+'/admin');await page.getByRole('button',{name:/Contact Messages/}).click();await page.getByText('Stored only (historical message; no backfill)',{exact:false}).waitFor();for(const text of['Queued for email','Delivery failed or unknown','Email service accepted (inbox arrival not confirmed)','Operator review needed'])await page.getByText(text,{exact:false}).waitFor();
 const retry=page.getByRole('button',{name:'Retry notification',exact:true});assert.equal(await retry.count(),1);assert.equal(await page.locator('.suggestion-card').first().locator('a[href^="mailto:"]').getAttribute('href'),'mailto:synthetic%40example.test');await retry.click();await page.getByRole('alert').filter({hasText:'retry could not be queued'}).waitFor();assert.equal(await retry.isEnabled(),true);retryMode='accepted';await retry.click();await page.getByRole('status').filter({hasText:'existing reference'}).waitFor();await fits();await page.screenshot({path:'qa/contact-costs/'+(live?'public-':'')+'admin-'+width+'.jpg',type:'jpeg',quality:65,fullPage:true});
 await page.goto(base+'/');if(await page.locator('#ow-fab').isVisible())await page.locator('#ow-fab').click();await page.getByText('Paid plan:',{exact:false}).waitFor();await page.locator('#ow-btn-apikey').click();await page.getByText('AI editing is bring your own key.',{exact:false}).waitFor();await fits();await page.screenshot({path:'qa/contact-costs/'+(live?'public-':'')+'costs-'+width+'.jpg',type:'jpeg',quality:65});
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);await context.close();console.log(width+': contact validation/failure/429/network/same-key retry/new message/crypto fallback; truthful stored/queued status; Terms/costs and synthetic admin delivery/retry states pass. All writes/mail intercepted, admin identity synthetic and game iframe a functional double; 0 real signups, messages, model calls or payments.');
}}finally{await browser.close();}
