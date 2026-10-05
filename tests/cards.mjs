// 單卡測試：node tests/cards.mjs [card_id]
import { serve, open, assert, sleep } from './lib.mjs';
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';

const only = process.argv[2];
const TESTS = {};
function cardTest(id, fn) { TESTS[id] = fn; }

async function withCard(id, fn, opts, { preset, patch } = {}) {
  const args = ['src/plugin.py', '--test', id];
  if (preset) args.push('--preset', JSON.stringify(preset));
  if (patch) args.push('--patch', JSON.stringify(patch));
  execFileSync('python3', args, { stdio: 'inherit' });
  const s = await serve(`dist/test-${id}.json`);
  const ui = await open(s.base, opts);
  try {
    await ui.clickText('開始遊戲', 4000).catch(() => {});
    await ui.waitText(/測試：/); await ui.advance();
    await sleep(1500);
    await fn(ui);
    assert(ui.errors.length === 0, `${id} 沒有頁面例外 ${ui.errors.join(';')}`);
  } finally { await ui.close(); s.kill(); }
}

// 編輯器預覽不送 init：直接開卡片 HTML，2 秒後要有內容
async function noInit(id, selector) {
  mkdirSync('dist', { recursive: true });
  execFileSync('python3', ['-c', `import sys;sys.path.insert(0,'src');import plugin;open('dist/raw-${id}.html','w').write(plugin.html('${id}'))`]);
  const { chromium } = await import('/home/ct/larch-preview/node_modules/playwright-core/index.mjs');
  const b = await chromium.launch({ executablePath: '/opt/google/chrome/chrome' });
  const p = await b.newPage();
  await p.goto('file://' + process.cwd() + `/dist/raw-${id}.html`);
  await sleep(2600);
  assert(await p.locator(selector).count() > 0, `${id} 沒收到 init 也會用預設資料啟動`);
  await b.close();
}

// ── 各卡測試 ──

cardTest('vocab', async (withCard, noInit) => {
  await noInit('vocab', 'button[data-ok]');
  const result = async ui => (await ui.waitText(/RESULT.*last_ok=(true|false)/)).match(/RESULT.*?last_ok=(true|false)/)[0];
  // 答對：got -1 → 1，learned +1；連點只算一次
  await withCard('vocab', async ui => {
    const f = await ui.frameWith('button[data-ok]');
    const ok = f.locator('button[data-ok="1"]');
    await ok.click(); await ok.click({ force: true }).catch(() => {});
    await f.locator('#okBtn').click();
    const t = await result(ui);
    assert(/got_jishu=1/.test(t) && /learned=1/.test(t) && /last_ok=true/.test(t), '答對：got=1、learned=1（連點只算一次）' + t);
  });
  // 答錯：got -1 → 0，learned 不變
  await withCard('vocab', async ui => {
    const f = await ui.frameWith('button[data-ok]');
    await f.locator('button[data-ok="0"]').first().click();
    const t = await result(ui);
    assert(/got_jishu=0/.test(t) && /learned=0/.test(t) && /last_ok=false/.test(t), '答錯：got=0、learned=0 ' + t);
  });
  // 主線錯過再答對（解釋完回來重答）：got 停在 0、learned 不加
  await withCard('vocab', async ui => {
    const f = await ui.frameWith('button[data-ok]');
    await f.locator('button[data-ok="1"]').click(); await f.locator('#okBtn').click();
    const t = await result(ui);
    assert(/got_jishu=0/.test(t) && /learned=0/.test(t), '主線錯過再答對：got=0、learned=0 ' + t);
  }, {}, { preset: { got_jishu: 0 } });
  // 複習卡答對：got 0 → 2，learned +1
  await withCard('vocab', async ui => {
    const f = await ui.frameWith('button[data-ok]');
    await f.locator('button[data-ok="1"]').click(); await f.locator('#okBtn').click();
    const t = await result(ui);
    assert(/got_jishu=2/.test(t) && /learned=1/.test(t), '複習答對：got=2、learned=1 ' + t);
  }, {}, { preset: { got_jishu: 0 }, patch: { review: true, retry: false } });
  // iPhone：選項點擊區 ≥44px、沒有橫向捲動
  await withCard('vocab', async ui => {
    const f = await ui.frameWith('button[data-ok]');
    const sizes = await f.locator('button[data-ok]').evaluateAll(bs => bs.map(b => [b.offsetWidth, b.offsetHeight]));
    assert(sizes.every(([w, h]) => w >= 44 && h >= 44), 'iPhone 選項 ≥44px ' + JSON.stringify(sizes));
    assert(await f.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'iPhone 沒有橫向捲動');
  }, { mobile: true });
});

for (const [id, fn] of Object.entries(TESTS)) if (!only || only === id) await fn(withCard, noInit);
