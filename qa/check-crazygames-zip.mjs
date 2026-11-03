// Play the CrazyGames zip like a player, served from an unzipped folder on loopback.
// offline: the plain zip must make no request outside the folder at all.
// sdk-fake: the SDK zip, with sdk.crazygames.com answered by a recorder, must report
//   init, loadingStart, loadingStop, gameplayStart, gameplayStop (pause), gameplayStart (resume).
// sdk-real: the SDK zip with the real CrazyGames SDK (local mode on 127.0.0.1); nothing reaches open-world.gg.
// Usage: node qa/check-crazygames-zip.mjs http://127.0.0.1:PORT <playwright/index.mjs> <offline|sdk-fake|sdk-real> [out-dir]
import assert from 'node:assert/strict';import {mkdir} from 'node:fs/promises';import {pathToFileURL} from 'node:url';
const base=process.argv[2].replace(/\/$/,''),mode=process.argv[4],out=process.argv[5]||'qa/crazygames';
assert.equal(new URL(base).hostname,'127.0.0.1');assert.ok(['offline','sdk-fake','sdk-real'].includes(mode));
const {chromium}=await import(pathToFileURL(process.argv[3]).href);await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:['--enable-unsafe-swiftshader']});
const FAKE_SDK=`window.__cg=[];window.CrazyGames={SDK:{environment:'crazygames',init:async()=>{__cg.push('init')},
 game:{loadingStart(){__cg.push('loadingStart')},loadingStop(){__cg.push('loadingStop')},gameplayStart(){__cg.push('gameplayStart')},gameplayStop(){__cg.push('gameplayStop')}}}};`;
try{for(const [width,options] of [[375,{viewport:{width:375,height:812},isMobile:true,hasTouch:true}],[1440,{viewport:{width:1440,height:900}}]]){
 const c=await browser.newContext(options),hosts=new Set(),blocked=[],errors=[];
 await c.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin===base)return route.continue();hosts.add(u.hostname);
  if(u.hostname.endsWith('open-world.gg')){blocked.push(u.href);return route.abort();}
  if(mode==='sdk-fake'&&u.href==='https://sdk.crazygames.com/crazygames-sdk-v3.js')return route.fulfill({contentType:'text/javascript',body:FAKE_SDK});
  if(mode==='sdk-real'&&u.hostname.endsWith('crazygames.com'))return route.continue();
  blocked.push(u.href);return route.abort();});
 const p=await c.newPage();p.setDefaultTimeout(90000);p.on('pageerror',e=>errors.push('pageerror: '+e.message));
 p.on('console',m=>{if(m.type()==='error')errors.push('console: '+m.text())});
 await p.goto(base+'/index.html');await p.locator('#overlay').waitFor({state:'visible'});await p.locator('canvas').first().waitFor({state:'attached'});
 await p.waitForLoadState('load');await p.waitForTimeout(1500);
 assert.equal(await p.title(),'Open World City Sandbox');assert.equal(await p.locator('link[rel=manifest]').count(),0,'no web app manifest');
 assert.equal(await p.evaluate(()=>getComputedStyle(document.body).userSelect),'none');
 await p.screenshot({path:`${out}/${mode}-start-${width}.jpg`,type:'jpeg',quality:75});
 if(width===375){await p.locator('body.mobile').waitFor({state:'attached'});await p.locator('#overlay').tap();}
 else await p.locator('#overlay').click();
 await p.locator('#overlay').waitFor({state:'hidden'});assert.equal(await p.locator('#hud').evaluate(el=>getComputedStyle(el).display),'block');
 assert.equal(await p.evaluate(()=>!!document.fullscreenElement),false,'the game does not take fullscreen itself');
 if(width===375&&mode==='offline'){await p.locator('#btn-veh-m').tap();await p.locator('#veh-menu').waitFor({state:'visible'});}
 else{await p.keyboard.down('KeyW');await p.waitForTimeout(1200);await p.keyboard.up('KeyW');}
 await p.waitForTimeout(2500);await p.screenshot({path:`${out}/${mode}-playing-${width}.jpg`,type:'jpeg',quality:75});
 // The Game Store portal marker never shows.
 assert.equal(await p.evaluate(()=>[...document.querySelectorAll('div')].filter(d=>/STORE/i.test(d.textContent||'')&&d.style.position==='fixed'&&d.style.opacity!=='0').length),0);
 if(mode==='sdk-fake'){
  if(width===1440){await p.keyboard.press('Escape');await p.locator('#pause-screen').waitFor({state:'visible'});await p.locator('#pause-screen').click();await p.locator('#pause-screen').waitFor({state:'hidden'});}
  else{await p.locator('#btn-pause').tap();await p.locator('#pause-screen').waitFor({state:'visible'});await p.locator('#pause-screen').tap();await p.locator('#pause-screen').waitFor({state:'hidden'});}
  await p.waitForTimeout(300);
  assert.deepEqual(await p.evaluate(()=>window.__cg),['init','loadingStart','loadingStop','gameplayStart','gameplayStop','gameplayStart']);
 }
 if(mode==='sdk-real'){const env=await p.evaluate(()=>window.CrazyGames&&window.CrazyGames.SDK&&window.CrazyGames.SDK.environment);console.log(width+': real SDK environment '+env);}
 assert.deepEqual(blocked,[],'blocked requests');if(mode==='offline')assert.deepEqual([...hosts],[],'offline zip requests nothing outside its folder');
 assert.ok(![...hosts].some(h=>h.endsWith('open-world.gg')),'no call to open-world.gg');
 assert.deepEqual(errors,[]);await c.close();
 console.log(`${width} ${mode}: start screen, one-tap/click start, HUD, ${width===375?(mode==='offline'?'vehicle menu':'touch play'):'movement'}, no portal marker, no fullscreen grab, no manifest; outside hosts: ${[...hosts].join(', ')||'none'}; zero page/console errors`);
}}finally{await browser.close();}
