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

for (const [id, fn] of Object.entries(TESTS)) if (!only || only === id) await fn(withCard, noInit);
