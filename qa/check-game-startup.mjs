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

async function freshGame(width) {
  const mobile = width === 375;
  const context = await browser.newContext({
    viewport: { width, height: 812 }, isMobile: mobile, hasTouch: mobile,
  });
  const page = await context.newPage();
  page.setDefaultTimeout(45000);
  const errors = [], writes = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (request.url() === origin + '/game/base' && request.headers().authorization) {
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
  await play.waitFor({ state: 'visible' });
  assert.equal(await frame.locator('#ow-base-status').isVisible(), false);
  assert.equal(await frame.locator('#ow-base-retry').isVisible(), false);
  assert.equal(await frame.locator('body').evaluate(() => {
    try { parent.localStorage.getItem('ow_token'); return 'readable'; }
    catch { return 'blocked'; }
  }), 'blocked');
  if (width === 375) await play.tap();
  else {
    await play.press('Tab');
    assert.equal(await play.isVisible(), true);
    assert.equal(await play.evaluate(button => document.activeElement !== button), true);
    await play.press('Escape');
    assert.equal(await play.isVisible(), true);
    await play.press(label === 'recovered' ? 'Space' : 'Enter');
  }
  await frame.locator('#overlay').waitFor({ state: 'hidden' });
  assert.equal(await frame.locator('#hud').evaluate(hud => getComputedStyle(hud).display), 'block');
  if (width === 375) {
    await frame.locator('body.playing').waitFor({ state: 'attached' });
    await frame.locator('#btn-shoot').waitFor({ state: 'visible' });
    await frame.locator('#btn-veh-m').tap();
    await frame.locator('#veh-menu.open').waitFor({ state: 'visible' });
    await frame.locator('body').evaluate(async () => {
      if (document.fullscreenElement) await document.exitFullscreen();
    });
  } else {
    await frame.locator('#bottom-bar').waitFor({ state: 'visible' });
  }
  await page.screenshot({ path: join(evidenceDir, 'game-' + label + '-' + width + '.jpg'), type: 'jpeg', quality: 80 });
  assert.deepEqual(errors, []);
  assert.deepEqual(writes, []);
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
      assert.equal(await iframe.getAttribute('src'), '/game/base');
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
      console.log(width + 'px: Loading during delay, one Start input reaches HUD and available controls.');
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
      console.log(width + 'px: Retry after a failed dependency reloads the real base and enables first play.');
    } finally {
      await failed.context.close();
    }
  }
} finally {
  await browser.close();
}
