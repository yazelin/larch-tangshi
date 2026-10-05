// 測試共用：開 larch-preview、讀所有 frame 的文字、按鍵
import { chromium, devices } from '/home/ct/larch-preview/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
export { devices };
export const sleep = ms => new Promise(r => setTimeout(r, ms));

export async function serve(json) {
  const proc = spawn('python3', ['/home/ct/larch-preview/serve.py', json, '--port', '0'], { stdio: ['ignore', 'pipe', 'inherit'] });
  const base = await new Promise((ok, bad) => {
    proc.stdout.on('data', d => { const m = d.toString().match(/預覽：(http:\/\/127\.0\.0\.1:\d+)/); if (m) ok(m[1]); });
    proc.on('exit', c => bad(new Error('serve.py exit ' + c)));
  });
  return { base, kill: () => proc.kill() };
}

export async function open(base, { mobile = false } = {}) {
  const browser = await chromium.launch({ executablePath: '/opt/google/chrome/chrome', headless: false });
  const ctx = await browser.newContext(mobile ? { ...devices['iPhone 13'], locale: 'zh-TW' } : { viewport: { width: 1280, height: 800 }, locale: 'zh-TW' });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(base.startsWith('http') && base.includes('/preview/') ? base : base + '/');
  await sleep(3500);
  const text = async () => (await Promise.all(page.frames().map(f => f.locator('body').innerText().catch(() => '')))).join(' | ').replace(/\s+/g, ' ');
  const waitText = async (re, ms = 15000) => {
    const end = Date.now() + ms;
    while (Date.now() < end) { const t = await text(); if (re.test(t)) return t; await sleep(250); }
    throw new Error('等不到 ' + re + '；畫面：' + (await text()).slice(0, 400));
  };
  const clickText = async (s, ms = 15000) => {
    const end = Date.now() + ms;
    while (Date.now() < end) {
      for (const f of page.frames()) { const l = f.getByText(s, { exact: false }); if (await l.count()) { await l.first().click(); return; } }
      await sleep(300);
    }
    throw new Error('找不到可點的「' + s + '」');
  };
  const frameWith = async (sel) => { for (const f of page.frames()) if (await f.locator(sel).count()) return f; return null; };
  // 前進一步：畫面上有對話卡的對話框就點它，否則按 Enter（RPG 地圖上的對話）
  const advance = async () => {
    for (const f of page.frames()) { const b = f.locator('.vn2-box'); if (await b.count() && await b.first().isVisible()) { await b.first().click(); return; } }
    await page.keyboard.press('Enter');
  };
  return { advance, browser, page, errors, text, waitText, clickText, frameWith, close: () => browser.close() };
}

export function assert(cond, msg) { if (!cond) throw new Error('FAIL: ' + msg); console.log('ok  ', msg); }
