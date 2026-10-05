// 單卡測試：node tests/cards.mjs [card_id]
import { serve, open, assert, sleep } from './lib.mjs';
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';

const only = process.argv[2];
const TESTS = {};
// 「好」按鈕剛出現時立刻點，偶爾會點在版面還在變的那一刻而沒觸發（1/6）。等卡片翻好再停 0.3 秒，跟真人一樣。
// 播放器把插件卡 iframe 往上放約 10.5% 畫面高（手機 -70px、桌機 -84px），卡片頂端的東西要在螢幕內
async function assertOnScreen(f, sel, label) {
  const box = await (await f.frameElement()).boundingBox();
  const top = await f.locator(sel).first().evaluate(e => e.getBoundingClientRect().top);
  assert(box.y + top >= 0, `${label}：${sel} 頂端在螢幕內（${Math.round(box.y + top)}px）`);
}
// 手指捲不動 overflow:hidden；看得到的字塊都要在 iframe 可見區（扣掉頂端偏移）與畫面內
async function assertTilesVisible(ui, f, label) {
  const box = await (await f.frameElement()).boundingBox();
  const vh = await ui.page.evaluate(() => innerHeight);
  const bottoms = await f.locator('.tile:not(.used)').evaluateAll(ts => ts.map(t => t.getBoundingClientRect().bottom));
  const worst = Math.max(...bottoms) + box.y;
  assert(worst <= Math.min(vh, box.y + box.height), `${label}：字塊都在畫面內（最低 ${Math.round(worst)} / ${vh}）`);
}
async function clickOk(f) { await f.locator('body.shown').waitFor(); await sleep(300); await f.locator('#okBtn').click(); }
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
    await clickOk(f);
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
    await f.locator('button[data-ok="1"]').click(); await clickOk(f);
    const t = await result(ui);
    assert(/got_jishu=0/.test(t) && /learned=0/.test(t), '主線錯過再答對：got=0、learned=0 ' + t);
  }, {}, { preset: { got_jishu: 0 } });
  // 複習卡答對：got 0 → 2，learned +1
  await withCard('vocab', async ui => {
    const f = await ui.frameWith('button[data-ok]');
    await f.locator('button[data-ok="1"]').click(); await clickOk(f);
    const t = await result(ui);
    assert(/got_jishu=2/.test(t) && /learned=1/.test(t), '複習答對：got=2、learned=1 ' + t);
  }, {}, { preset: { got_jishu: 0 }, patch: { review: true, retry: false } });
  // iPhone：選項點擊區 ≥44px、沒有橫向捲動、大字在螢幕內
  await withCard('vocab', async ui => {
    const f = await ui.frameWith('button[data-ok]');
    await assertOnScreen(f, '#word', 'iPhone 生字卡');
    const sizes = await f.locator('button[data-ok]').evaluateAll(bs => bs.map(b => [b.offsetWidth, b.offsetHeight]));
    assert(sizes.every(([w, h]) => w >= 44 && h >= 44), 'iPhone 選項 ≥44px ' + JSON.stringify(sizes));
    assert(await f.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'iPhone 沒有橫向捲動');
  }, { mobile: true });
});

cardTest('follow', async (withCard, noInit) => {
  await noInit('follow', '.ch');
  await withCard('follow', async ui => {
    const f = await ui.frameWith('.ch');
    await assertOnScreen(f, '#label', '跟念卡');
    assert(await f.locator('.ch').count() === 10, '十個字');
    await f.locator('#okBtn').waitFor({ state: 'visible', timeout: 12000 });
    assert(await f.locator('.ch.lit').count() === 10, '念完十個字都點亮');
    await sleep(300); await f.locator('#okBtn').click();
    await ui.waitText(/RESULT/);
  });
  // 音檔載入失敗（404）也不能卡死：照樣逐字點亮、出現「好」
  await withCard('follow', async ui => {
    const f = await ui.frameWith('.ch');
    await f.locator('#okBtn').waitFor({ state: 'visible', timeout: 12000 });
    assert(await f.locator('.ch.lit').count() === 10, '音檔 404：十個字照樣點亮、出現「好」');
    await sleep(300); await f.locator('#okBtn').click();
    await ui.waitText(/RESULT/);
  }, undefined, { patch: { audio: '/files/assets/nope.mp3' } });
});

cardTest('order', async (withCard, noInit) => {
  await noInit('order', '.slot');
  await withCard('order', async ui => {
    const f = await ui.frameWith('.slot');
    await assertOnScreen(f, '#tip', '排圖卡');
    for (let i = 0; i < 4; i++) {           // 選擇排序：第 i 格放 data-idx=i 的那張
      const idx = await f.locator('.slot').evaluateAll(s => s.map(b => +b.dataset.idx));
      const j = idx.indexOf(i);
      if (j !== i) { await f.locator('.slot').nth(i).click(); await f.locator('.slot').nth(j).click(); }
    }
    await f.locator('#okBtn').waitFor({ state: 'visible' }); await sleep(300); await f.locator('#okBtn').click();
    await ui.waitText(/RESULT/);
    assert(true, '四張圖排好可以往下');
  });
});

cardTest('recite', async (withCard, noInit) => {
  await noInit('recite', '.tile');
  await withCard('recite', async ui => {
    const f = await ui.frameWith('.tile');
    await assertOnScreen(f, '#round', 'iPhone 背誦卡');
    let wrongOnce = false;
    while (await f.locator('.blank:not(.filled)').count()) {
      await assertTilesVisible(ui, f, 'iPhone 背誦 ' + await f.locator('#round').innerText());
      const need = await f.locator('.blank:not(.filled)').first().getAttribute('data-ch');
      if (!wrongOnce) { await f.locator(`.tile:not([data-ch="${need}"])`).first().click(); wrongOnce = true; }
      await f.locator(`.tile[data-ch="${need}"]:not(.used)`).first().click();
      await sleep(120);
      if (!(await f.locator('.blank:not(.filled)').count())) await sleep(1000);   // 換關
    }
    await f.locator('#okBtn').waitFor({ state: 'visible' }); await sleep(300); await f.locator('#okBtn').click();
    const t = await ui.waitText(/RESULT stars=\d/);
    assert(/stars=3/.test(t), '三關錯 ≤2 次 → 3 顆星：' + t.match(/RESULT stars=\d/)[0]);
  }, { mobile: true });
});

for (const [id, fn] of Object.entries(TESTS)) if (!only || only === id) await fn(withCard, noInit);
