// Public owned-site QA. Fresh anonymous contexts; never reads a personal profile.
import assert from 'node:assert/strict';
import {chromium} from '../.runtime/allowance-qa/node_modules/playwright/index.mjs';
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
try{
 for(const width of [375,1440]){
  const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage(),errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('https://open-world.gg/rosebud-alternative',{waitUntil:'domcontentloaded'});
  const copy=page.getByText(/OpenWorld offers up to two included text attempts/);
  await copy.waitFor();await copy.scrollIntoViewIfNeeded();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.equal(/November 3|2026-11-03/.test(await page.locator('body').innerText()),false);
  await page.screenshot({path:`qa/allowance-rosebud-${width}.png`});
  await page.getByRole('article').getByRole('link',{name:'Play OpenWorld now',exact:true}).click();
  await page.locator('#ow-included-status').filter({hasText:'2 included attempts'}).waitFor();
  assert.equal(await page.locator('#ow-funding').inputValue(),'included');
  assert.equal(await page.getByRole('button',{name:'Sign In',exact:true}).count(),1);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.screenshot({path:`qa/allowance-guest-${width}.png`});
  console.log(`${width}px: revised conditional copy, no stale end date, guest 2 included attempts, included mode, no signup/key prompt, no horizontal overflow. Page errors: ${errors.length}.`);
  assert.deepEqual(errors,[]);
  await context.close();
 }
}finally{await browser.close();}
