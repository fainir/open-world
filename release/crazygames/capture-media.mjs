// Draft CrazyGames covers and preview clips from the real portal build (no HUD, title only on covers).
// Serve an unzipped openworld-crazygames.zip on 127.0.0.1, then:
//   node release/crazygames/capture-media.mjs http://127.0.0.1:PORT <playwright/index.mjs> <out-dir>
// Covers: 1920x1080, 800x1200, 800x800 PNG. Clips: 1920x1080 and 1080x1620 silent H.264 MP4, 18 s, built from
// DevTools screencast frames with the system ffmpeg (opening frame = the cover view, no cursor, no text).
import assert from 'node:assert/strict';import {mkdir,writeFile,rm} from 'node:fs/promises';import {pathToFileURL} from 'node:url';import {spawnSync} from 'node:child_process';
const base=process.argv[2].replace(/\/$/,''),out=process.argv[4];assert.equal(new URL(base).hostname,'127.0.0.1');assert.ok(out);
const {chromium}=await import(pathToFileURL(process.argv[3]).href);await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:['--enable-unsafe-swiftshader']});
const HIDE='#hud,#bottom-bar,#controls-bar,#weapon-hud,#btn-pause,#mobile-controls,#tip,#vehicle-prompt,#crosshair,#score,#combo,#tricks-panel{display:none!important}*{cursor:none!important}';
async function fly(p){
 await p.goto(base+'/index.html');await p.locator('#overlay').waitFor({state:'visible'});await p.waitForLoadState('load');
 await p.addStyleTag({content:HIDE});await p.locator('#overlay').click();await p.locator('#overlay').waitFor({state:'hidden'});
}
async function title(p,size){
 await p.evaluate(size=>{const t=document.createElement('div');t.textContent='Open World City Sandbox';
  t.style.cssText=`position:fixed;left:0;right:0;bottom:7%;text-align:center;z-index:99;color:#fff;font:900 ${size}px/1.05 'Segoe UI',Arial,sans-serif;letter-spacing:.02em;text-shadow:0 4px 18px rgba(0,0,0,.65),0 2px 0 rgba(0,0,0,.4);padding:0 6%`;
  document.body.appendChild(t)},size);
}
try{
 for(const [name,width,height,size] of [['cover-landscape-1920x1080',1920,1080,120],['cover-portrait-800x1200',800,1200,92],['cover-square-800x800',800,800,78]]){
  const c=await browser.newContext({viewport:{width,height},deviceScaleFactor:1}),p=await c.newPage();p.setDefaultTimeout(90000);
  await fly(p);await p.keyboard.down('KeyW');await p.waitForTimeout(1200);await p.keyboard.up('KeyW');await p.waitForTimeout(2500);
  await title(p,size);await p.screenshot({path:`${out}/${name}.png`});await c.close();console.log('cover',name);
 }
 for(const [name,width,height] of [['preview-landscape-1920x1080',1920,1080],['preview-portrait-1080x1620',1080,1620]]){
  const c=await browser.newContext({viewport:{width,height},deviceScaleFactor:1}),p=await c.newPage();p.setDefaultTimeout(90000);
  await fly(p);const frames=`${out}/.frames-${name}`;await mkdir(frames,{recursive:true});
  const cdp=await c.newCDPSession(p),list=[];
  cdp.on('Page.screencastFrame',async f=>{const file=`${frames}/${String(list.length).padStart(5,'0')}.jpg`;list.push({file,t:f.metadata.timestamp});
   await writeFile(file,Buffer.from(f.data,'base64'));cdp.send('Page.screencastFrameAck',{sessionId:f.sessionId}).catch(()=>{});});
  await cdp.send('Page.startScreencast',{format:'jpeg',quality:90,maxWidth:width,maxHeight:height});
  await p.keyboard.down('KeyW');await p.waitForTimeout(1200);await p.keyboard.up('KeyW');await p.waitForTimeout(6000);
  await p.keyboard.down('KeyW');await p.keyboard.down('ShiftLeft');await p.waitForTimeout(6000);await p.keyboard.up('ShiftLeft');await p.keyboard.up('KeyW');
  await p.keyboard.down('KeyA');await p.waitForTimeout(3000);await p.keyboard.up('KeyA');await p.waitForTimeout(3000);
  await cdp.send('Page.stopScreencast');await p.waitForTimeout(300);await c.close();
  const lines=list.map((f,i)=>`file '${f.file}'\nduration ${Math.max(0.001,((list[i+1]||f).t-f.t)||1/30).toFixed(4)}`);
  await writeFile(`${frames}/list.txt`,lines.join('\n')+`\nfile '${list.at(-1).file}'\n`);
  const r=spawnSync('ffmpeg',['-y','-loglevel','error','-f','concat','-safe','0','-i',`${frames}/list.txt`,'-t','18','-r','30','-vf',`scale=${width}:${height},format=yuv420p`,
   '-c:v','libx264','-preset','slow','-crf','27','-an','-movflags','+faststart',`${out}/${name}.mp4`],{stdio:'inherit'});
  assert.equal(r.status,0,'ffmpeg');await rm(frames,{recursive:true});console.log('clip',name,list.length,'frames');
 }
}finally{await browser.close();}
