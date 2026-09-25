/* Optional real-browser checks. See README for the isolated Playwright install. */
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const requests = [];
    const errors = [];
    page.on('request', r => requests.push(r.url()));
    page.on('pageerror', e => errors.push(e.message));
    const url = pathToFileURL(path.resolve(__dirname, '../index.html')).href;
    await page.goto(url);
    const row = id => page.locator(`.plugin-row[data-id="${id}"]`);
    const order = () => page.locator('.plugin-row').evaluateAll(nodes => nodes.map(n => n.dataset.id));
    const selected = () => page.locator('.demo-email-section').evaluateAll(nodes => nodes.map(n => n.dataset.plugin));
    assert.equal(await page.locator('.plugin-row').count(), 30);
    assert.deepEqual(await selected(), ['weather', 'quote', 'headlines', 'ai_pricing', 'crypto']);
    assert.equal(await page.locator('[data-plugin="ai_pricing"] h5').count(), 3);

    await row('weather').locator('input').uncheck();
    assert.equal(await page.locator('[data-plugin="weather"]').count(), 0);
    await row('weather').locator('input').check();
    assert.equal((await order())[0], 'weather');
    await row('weather').getByRole('button', { name: 'Move Weather down', exact: true }).click();
    assert.equal((await order())[1], 'weather');
    assert.equal(await page.locator(':focus').getAttribute('aria-label'), 'Move Weather down');
    await row('weather').locator('.drag-handle').focus();
    await page.keyboard.press('ArrowUp');
    assert.equal((await order())[0], 'weather');
    assert.equal(await page.locator(':focus').getAttribute('aria-label'), 'Reorder Weather');

    // Mouse drag after a target, plus Escape cancellation.
    const drag = async cancel => {
      await row('weather').locator('.drag-handle').scrollIntoViewIfNeeded();
      const from = await row('weather').locator('.drag-handle').boundingBox();
      const to = await row('air_quality').boundingBox();
      await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
      await page.mouse.down();
      await page.mouse.move(to.x + 80, to.y + to.height - 10, { steps: 10 });
      if (cancel) await page.keyboard.press('Escape');
      await page.mouse.up();
    };
    await drag(true);
    assert.equal((await order())[0], 'weather');
    await drag(false);
    assert.equal((await order())[1], 'weather');
    const movedOrder = await order();
    await row('weather').locator('input').uncheck();
    await row('weather').locator('input').check();
    assert.deepEqual(await order(), movedOrder);

    // Filtering does not change the selected preview or discard hidden order.
    const beforeFilter = await selected();
    await page.locator('#plugin-search').fill('semantic');
    assert.equal(await page.locator('.plugin-row').count(), 1);
    assert.deepEqual(await selected(), beforeFilter);
    await row('semantic_scholar').locator('input').check();
    await row('semantic_scholar').locator('[data-action="up"]').click();
    await page.locator('#plugin-search').fill('');
    assert.equal(await page.locator('.plugin-row').count(), 30);
    await page.locator('#plugin-category').selectOption('Markets');
    assert.equal(await page.locator('.plugin-row').count(), 3);
    await page.locator('#plugin-search').fill('zzzz');
    assert.equal(await page.locator('#no-plugins').isVisible(), true);
    await page.locator('#demo-clear').click();
    assert.equal((await selected()).length, 0);
    assert.equal(await page.locator('#demo-sections .demo-empty').count(), 1);
    await page.locator('#demo-reset').click();
    assert.equal(await page.locator('.plugin-row').count(), 30);
    assert.equal((await selected()).length, 5);
    assert.equal((await order())[0], 'weather');
    for (const checkbox of await page.locator('.plugin-row input').all()) await checkbox.check();
    assert.equal((await selected()).length, 30);
    await page.reload();
    assert.equal((await selected()).length, 5);
    assert.equal((await order())[0], 'weather');
    await page.locator('#plugin-builder').screenshot({ path: '/tmp/email-brief-builder-desktop.png' });
    assert.ok(requests.every(r => r.startsWith('file:')), requests.join('\n'));
    assert.deepEqual(errors, []);

    const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    const phone = await mobile.newPage();
    await phone.goto(url);
    await phone.locator('#plugin-builder').scrollIntoViewIfNeeded();
    assert.ok(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    await phone.locator('[data-id="weather"] [data-action="down"]').tap();
    assert.equal(await phone.locator('.plugin-row').nth(1).getAttribute('data-id'), 'weather');
    await phone.locator('#demo-reset').tap();
    // Actual touch events via CDP exercise the pointer drag path.
    const session = await mobile.newCDPSession(phone);
    await phone.locator('[data-id="weather"] .drag-handle').scrollIntoViewIfNeeded();
    const from = await phone.locator('[data-id="weather"] .drag-handle').boundingBox();
    const to = await phone.locator('[data-id="air_quality"]').boundingBox();
    const x = from.x + from.width / 2;
    await session.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y: from.y + 20 }] });
    for (let step = 1; step <= 8; step++) {
      const y = from.y + 20 + ((to.y + to.height - 10) - (from.y + 20)) * step / 8;
      await session.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y }] });
    }
    await session.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    assert.equal(await phone.locator('.plugin-row').nth(1).getAttribute('data-id'), 'weather');
    await phone.locator('#plugin-builder').screenshot({ path: '/tmp/email-brief-builder-mobile.png' });
    await mobile.close();

    const noJS = await browser.newContext({ javaScriptEnabled: false });
    const fallback = await noJS.newPage();
    await fallback.goto(url);
    assert.ok(await fallback.locator('noscript').isVisible());
    assert.ok(await fallback.locator('#setup').isVisible());
    assert.ok(await fallback.locator('.catalog-summary').isVisible());
    assert.equal(await fallback.locator('#demo-interactive').isVisible(), false);
    await noJS.close();
    console.log('PASS: desktop, keyboard, mouse drag/cancel, touch drag, mobile, filters, all plugins, no-JS, and no external requests.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
