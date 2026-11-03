// One-tap share helper: share sheet first, copy as the fallback. Usage: node --test qa/share-link.test.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function load({share,clipboard}={}){
 const calls=[],window={},navigator={};
 if(share)navigator.share=async data=>{calls.push(['share',data]);return share(data)};
 navigator.clipboard={writeText:async text=>{calls.push(['copy',text]);if(clipboard==='blocked')throw Object.assign(Error('blocked'),{name:'NotAllowedError'})}};
 vm.runInNewContext(fs.readFileSync('app/static/js/share-link.js','utf8'),{window,navigator});
 return {share:(...a)=>window.OWShare(...a),calls};
}
const url='https://open-world.gg/shared/abc';
test('the share sheet is used when the device has one',async()=>{const s=load({share:()=>{}});assert.equal(await s.share(url,'T','X'),'shared');assert.equal(JSON.stringify(s.calls),JSON.stringify([['share',{title:'T',text:'X',url}]]));});
test('closing the share sheet copies nothing',async()=>{const s=load({share:()=>{throw Object.assign(Error('closed'),{name:'AbortError'})}});assert.equal(await s.share(url,'T','X'),'cancelled');assert.equal(s.calls.length,1);});
test('a blocked share sheet falls back to copying the link',async()=>{const s=load({share:()=>{throw Object.assign(Error('no gesture'),{name:'NotAllowedError'})}});assert.equal(await s.share(url,'T','X'),'copied');assert.deepEqual(s.calls.at(-1),['copy',url]);});
test('no share sheet copies the link',async()=>{const s=load();assert.equal(await s.share(url,'T','X'),'copied');assert.deepEqual(s.calls,[['copy',url]]);});
test('no share sheet and a blocked clipboard asks the page to show the link',async()=>{const s=load({clipboard:'blocked'});assert.equal(await s.share(url,'T','X'),'manual');});
