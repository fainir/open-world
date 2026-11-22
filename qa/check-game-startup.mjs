// Exercise the real game with read-only browser traffic. No model calls.
import assert from 'node:assert/strict';
import { lstat, mkdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const [fixtureFile, entry, evidenceDir = 'qa/perf'] = process.argv.slice(2);
let origin = 'https://open-world.gg';
if (fixtureFile !== '--live') {
  const stat = await lstat(fixtureFile);
  assert.ok(stat.isFile() && !(stat.mode & 0o077));
  const fixture = JSON.parse(await readFile(fixtureFile, 'utf8'));
  assert.equal(new URL(fixture.base).hostname, '127.0.0.1');
  assert.equal(fixture.synthetic, true);
  assert.equal(fixture.scope, 'real base game');
  origin = fixture.base;
}
await mkdir(evidenceDir, { recursive: true });
const { chromium } = await import(pathToFileURL(entry).href);
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--enable-unsafe-swiftshader'] });
const three = 'https://cdn.jsdelivr.net/npm/three@*/build/three.module.js';

async function freshGame(width, height = 812) {
  const mobile = width <= 375;
  const context = await browser.newContext({
    viewport: { width, height }, isMobile: mobile, hasTouch: mobile,
  });
  const page = await context.newPage();
  page.setDefaultTimeout(45000);
  const errors = [], writes = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (request.url().startsWith(origin + '/game/base') && request.headers().authorization) {
      errors.push('The public base iframe received a credential header');
    }
  });
  await context.route('**/*', route => {
    const request = route.request();
    if (!['GET', 'HEAD'].includes(request.method())) {
      writes.push(request.method());
      return route.abort();
    }
    return route.continue();
  });
  const frame = page.frameLocator('#ow-game');
  return { context, page, frame, errors, writes };
}

async function verifyReady(game, width, label) {
  const { page, frame, errors, writes } = game;
  const play = frame.getByRole('button', { name: /start game|tap to play/i });
  await frame.locator('#overlay').waitFor({ state: 'hidden' });
  assert.equal(await play.isVisible(), false);
  assert.equal(await frame.locator('#ow-base-status').isVisible(), false);
  assert.equal(await frame.locator('#ow-base-retry').isVisible(), false);
  assert.equal(await page.locator('#ow-panel').getAttribute('aria-hidden'), 'true');
  const fillsViewport = await page.locator('#ow-game').evaluate(iframe =>
    iframe.clientWidth === innerWidth && iframe.clientHeight === innerHeight);
  assert.ok(fillsViewport);
  assert.equal(await frame.locator('body').evaluate(() => {
    try { parent.localStorage.getItem('ow_token'); return 'readable'; }
    catch { return 'blocked'; }
  }), 'blocked');
  assert.equal(await frame.locator('#hud').evaluate(hud => getComputedStyle(hud).display), 'block');
  const guide = frame.locator('#ow-play-guide');
  await guide.waitFor();
  assert.ok((await guide.locator('p').textContent()).length > 12);
  if (width === 375) {
    await frame.locator('body.playing').waitFor({ state: 'attached' });
    await frame.locator('#btn-shoot').waitFor({ state: 'visible' });
    const dimensions = await frame.locator('#game').evaluate(canvas => ({
      width: canvas.clientWidth, height: canvas.clientHeight, windowWidth: innerWidth, windowHeight: innerHeight,
    }));
    assert.equal(dimensions.width, dimensions.windowWidth);
    assert.equal(dimensions.height, dimensions.windowHeight);
    assert.ok(dimensions.width > dimensions.height);
    await frame.getByRole('button', { name: 'Full screen', exact: true }).waitFor();
    await frame.locator('#btn-veh-m').tap();
    await frame.locator('#veh-menu.open').waitFor({ state: 'visible' });
    await frame.locator('#veh-close').tap();
    await frame.locator('#veh-menu.open').waitFor({ state: 'hidden' });
    await frame.locator('body').evaluate(async () => {
      if (document.fullscreenElement) await document.exitFullscreen();
    });
    await page.setViewportSize({ width: 812, height: 375 });
    // Update the physical screen metrics for touch routing into the opaque frame.
    const device = await page.context().newCDPSession(page);
    await device.send('Emulation.setDeviceMetricsOverride', {
      width: 812, height: 375, screenWidth: 812, screenHeight: 375, deviceScaleFactor: 1, mobile: true,
      screenOrientation: { type: 'landscapePrimary', angle: 90 },
    });
    await frame.locator('body:not([style*="rotate(90deg)"])').waitFor();
    assert.deepEqual(await frame.locator('#game').evaluate(canvas => [canvas.clientWidth, canvas.clientHeight]), [812, 375]);
    await frame.locator('#btn-char-m').tap();
    await frame.locator('#char-menu .subtitle').filter({hasText:'Tap a choice'}).waitFor();
    await frame.locator('#char-close').tap();
    await frame.locator('#char-menu.open').waitFor({ state: 'hidden' });
    await frame.locator('#btn-pause').tap();
    await frame.locator('#pause-screen').waitFor({ state: 'visible' });
    await frame.locator('#pause-screen').tap();
    await frame.locator('#pause-screen').waitFor({ state: 'hidden' });
  } else {
    assert.equal(await guide.getByText('X / click',{exact:true}).count(), 1);
    await page.waitForFunction(() => document.activeElement?.id === 'ow-game');
    await page.keyboard.press('v');
    await frame.locator('#veh-menu.open').waitFor();
    await frame.locator('#veh-menu .subtitle').filter({hasText:'arrows and Enter'}).waitFor();
    await page.keyboard.press('Escape');
    await frame.locator('#veh-menu.open').waitFor({ state: 'hidden' });
  }
  await page.screenshot({ path: join(evidenceDir, 'game-' + label + '-' + width + '.jpg'), type: 'jpeg', quality: 80 });
  assert.deepEqual(errors, []);
  assert.deepEqual(writes, []);
}

async function startActivity({page,frame},id,label,touch) {
  const guide = frame.locator('#ow-play-guide');
  // Place the test player at the real activity entrance. The following inputs use its UI.
  await page.route('**/game/base?autoplay=1', async route => {
    const response = await route.fetch();
    const html = await response.text();
    const marker = 'cityPlayGuide.update();';
    assert.ok(html.includes(marker));
    await route.fulfill({response,body:html.replace(marker,marker+`
window.approachGuideTest = id => {
  const zone = zoneManager.zones.find(candidate => candidate.id === id);
  const [x,,z] = zone.position;
  P.set(x, Math.max(getH(x,z),getSurfaceH(x,z)) + .15, z);
  V.set(0,0,0); hVel.set(0,0); mode='walk'; isFlying=false; onGround=true;
};
window.guideActivityReady = () => !!zoneManager.activeZone && !zoneManager.transitioning;`)});
  });
  await page.goto(origin, {waitUntil:'commit'});
  await guide.waitFor();
  await frame.locator('body').evaluate((_,id) => window.approachGuideTest(id),id);
  await guide.getByText('Choose Enter to start '+label+'.',{exact:true}).waitFor();
  if (touch) await frame.locator('#btn-enter').tap();
  else await page.keyboard.press('e');
  await guide.locator('strong').getByText(label,{exact:true}).waitFor();
  const gameplay=await (await page.locator('#ow-game').elementHandle()).contentFrame();
  await gameplay.waitForFunction(()=>window.guideActivityReady());
  return guide;
}

async function verifyActivityGuide(touch) {
  const game = await freshGame(touch ? 375 : 1440);
  const { context, page, frame } = game;
  try {
    const guide=await startActivity(game,'diving-contest','Diving Contest',touch);
    const choice=guide.locator('ul').getByText('Medium',{exact:true});
    if (touch) await guide.getByRole('button',{name:'Medium',exact:true}).tap();
    else{await choice.waitFor();await page.keyboard.press('2',{delay:70});}
    await guide.locator('p').filter({hasText:'Jump from the board'}).waitFor();
    if (touch) await frame.locator('#btn-jump').tap();
    else await page.keyboard.press('Space',{delay:70});
    await guide.locator('p').filter({hasText:'Flip as you fall'}).waitFor();
    if (touch) await frame.locator('#btn-jump').tap();
    else await page.keyboard.press('Space',{delay:70});
    await page.screenshot({path:join(evidenceDir,'guide-dive-'+(touch?'touch':'desktop')+'.jpg'),quality:82});
    await frame.getByText(/^1 flip \+/).waitFor({state:'attached'});
    if (touch) await frame.locator('#btn-enter').tap();
    else await page.keyboard.press('e');
    await guide.getByText(/Choose Enter to start Diving Contest/).waitFor();
    assert.deepEqual(game.errors, []);
    assert.deepEqual(game.writes, []);
    console.log((touch?'Touch':'Desktop')+' follows the diving guide from approach and height selection through the jump, flip and exit.');
  } finally {
    await context.close();
  }
}

async function verifyCompactActivities() {
  const arcade=await freshGame(320,568);
  try {
    const guide=await startActivity(arcade,'arcade','Arcade',true);
    await guide.getByRole('button',{name:'Breakout',exact:true}).tap();
    const canvas=arcade.frame.locator('#ow-arcade-canvas');
    await canvas.waitFor();
    await guide.getByText('Breakout',{exact:true}).waitFor();
    const [card,board]=await Promise.all([guide.boundingBox(),canvas.boundingBox()]);
    assert.ok(card.x+card.width<=board.x||board.x+board.width<=card.x||
      card.y+card.height<=board.y||board.y+board.height<=card.y,'The Arcade board covers the guide.');
    await arcade.page.screenshot({path:join(evidenceDir,'guide-arcade-touch.jpg'),quality:82});
    assert.deepEqual(arcade.errors, []);
    assert.deepEqual(arcade.writes, []);
  } finally {
    await arcade.context.close();
  }

  const gallery=await freshGame(320,568);
  try {
    const guide=await startActivity(gallery,'shooting-gallery','Shooting Gallery',true);
    const frame=gallery.frame,ammo=frame.locator('#ow-gallery-ammo');
    await ammo.getByText('●●●●●●',{exact:true}).waitFor();
    await frame.locator('#btn-shoot').tap();
    await ammo.getByText('●●●●●○',{exact:true}).waitFor();
    await guide.getByRole('button',{name:'Reload',exact:true}).tap();
    await ammo.getByText('●●●●●●',{exact:true}).waitFor();
    const card=await guide.boundingBox();
    assert.ok(card.x+card.width<160||card.x>160,'The touch guide covers the crosshair.');
    assert.deepEqual(gallery.errors, []);
    assert.deepEqual(gallery.writes, []);
  } finally {
    await gallery.context.close();
  }
  console.log('Compact 320px touch viewport keeps the arcade board and crosshair clear, and quick Shoot and Reload work.');
}

try {
  for (const width of [375, 1440]) {
    const delayed = await freshGame(width);
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    await delayed.page.route(three, async route => {
      await gate;
      await route.continue();
    }, { times: 1 });
    try {
      await Promise.all([
        delayed.page.waitForRequest(three, { timeout: 15000 }),
        delayed.page.goto(origin, { waitUntil: 'commit' }),
      ]);
      const iframe = delayed.page.locator('#ow-game');
      await iframe.waitFor({ state: 'visible' });
      assert.equal(await iframe.getAttribute('src'), '/game/base?autoplay=1');
      assert.equal(await iframe.getAttribute('srcdoc'), null);
      assert.equal(await iframe.getAttribute('sandbox'), 'allow-scripts allow-pointer-lock');
      const status = delayed.frame.getByText('Loading game…', { exact: true });
      await status.waitFor({ state: 'visible' });
      assert.equal(await status.evaluate(element => getComputedStyle(element).color), 'rgb(255, 255, 255)');
      assert.equal(await delayed.frame.locator('#ow-base-play').isVisible(), false);
      assert.equal(await delayed.frame.locator('#ow-base-retry').isVisible(), false);
      if (width === 375) await status.tap();
      else await status.click();
      assert.equal(await status.isVisible(), true);
      assert.equal(await delayed.frame.locator('#hud').isVisible(), false);
      if (width === 375) await delayed.page.screenshot({ path: join(evidenceDir, 'game-loading-375.jpg'), type: 'jpeg', quality: 80 });
      release();
      await verifyReady(delayed, width, 'ready');
      console.log(width + 'px: Loading during delay, then direct play with the HUD and working controls.');
    } finally {
      release();
      await delayed.context.close();
    }

    const failed = await freshGame(width);
    await failed.page.route(three, route => route.abort('failed'), { times: 1 });
    try {
      await failed.page.goto(origin, { waitUntil: 'commit' });
      const retry = failed.frame.getByRole('button', { name: 'Retry', exact: true });
      await retry.waitFor({ state: 'visible' });
      const errorMessage = failed.frame.getByText('The game could not load.', { exact: true });
      assert.equal(await errorMessage.isVisible(), true);
      assert.equal(await errorMessage.evaluate(element => getComputedStyle(element).color), 'rgb(255, 255, 255)');
      assert.equal(await failed.frame.locator('#ow-base-play').isVisible(), false);
      if (width === 375) await failed.page.screenshot({ path: join(evidenceDir, 'game-retry-375.jpg'), type: 'jpeg', quality: 80 });
      if (width === 375) await retry.tap();
      else await retry.press('Enter');
      await verifyReady(failed, width, 'recovered');
      console.log(width + 'px: Retry after a failed dependency reloads straight into the playable game.');
    } finally {
      await failed.context.close();
    }
  }
  await verifyActivityGuide(false);
  await verifyActivityGuide(true);
  await verifyCompactActivities();
} finally {
  await browser.close();
}
