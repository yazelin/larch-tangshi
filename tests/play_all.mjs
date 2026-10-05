// 全路徑：node tests/play_all.mjs [right|wrong|all]
import { serve, open, assert, sleep } from './lib.mjs';
import { execFileSync } from 'node:child_process';
execFileSync('python3', ['src/build.py'], { stdio: 'inherit' });
const which = process.argv[2] || 'all';
// 每個核心字解釋的第一句：對話框出現它就算進了一次解釋分支（預覽器側欄會列出卡片標題，不能用標題判斷）
const EXPLAIN = JSON.parse(execFileSync('python3', ['-c', "import sys,json;sys.path.insert(0,'src');import script;print(json.dumps([v[0][1] for v in script.load()['explain'].values()], ensure_ascii=False))"]).toString());
async function boxText(ui) { for (const f of ui.page.frames()) { const b = f.locator('.vn2-box'); if (await b.count() && await b.first().isVisible()) return b.first().innerText(); } return ''; }
const visible = async (f, sel) => f && await f.locator(sel).first().isVisible().catch(() => false);

async function run(mode) {   // right＝全對；wrong＝每個核心字第一次先答錯
  const s = await serve('dist/project.json');
  const ui = await open(s.base, { mobile: true });
  const wrongDone = new Set(); let explains = 0, reviews = 0, lastExplain = '';
  try {
    await ui.clickText('開始遊戲', 4000).catch(() => {});
    for (let step = 0; step < 800; step++) {
      const t = await ui.text();
      if (process.env.TRACE) console.log(step, 'BOX', (await boxText(ui)).slice(0, 40), '| T', t.split(' | ').slice(1).join(' | ').slice(0, 60));
      if (/學會了 \d+ 個字（一共 \d+ 個）/.test(t)) break;
      const body = t.split(' | ').slice(1).join(' ');   // 去掉預覽器側欄（卡片標題清單）
      const hit = EXPLAIN.find(x => body.includes(x.slice(0, 4)));   // 台詞逐字打出，只比前四字
      if (hit && hit !== lastExplain) { explains++; lastExplain = hit; }
      const v = await ui.frameWith('button[data-ok]');
      if (await visible(v, 'button[data-ok]')) {
        const word = await v.locator('#word').innerText();
        const review = await v.evaluate(() => document.body.dataset.review === '1');
        if (review) reviews++;
        const wrong = mode === 'wrong' && !review && !wrongDone.has(word);
        if (wrong) wrongDone.add(word);
        lastExplain = '';
        await v.locator(`button[data-ok="${wrong ? 0 : 1}"]`).first().click();
        if (!wrong) { await v.locator('body.shown').waitFor(); await sleep(300); await v.locator('#okBtn').click(); }
        await sleep(1200); continue;
      }
      const o = await ui.frameWith('.slot');
      if (await visible(o, '.slot')) {
        for (let i = 0; i < 4; i++) {
          const idx = await o.locator('.slot').evaluateAll(x => x.map(b => +b.dataset.idx));
          const j = idx.indexOf(i);
          if (j !== i) { await o.locator('.slot').nth(i).click(); await o.locator('.slot').nth(j).click(); }
        }
        await sleep(300); await o.locator('#okBtn').click(); await sleep(1200); continue;
      }
      const r = await ui.frameWith('.tile');
      if (r && await r.locator('.blank:not(.filled)').count()) {
        const need = await r.locator('.blank:not(.filled)').first().getAttribute('data-ch');
        await r.locator(`.tile[data-ch="${need}"]:not(.used)`).first().click(); await sleep(150);
        if (!(await r.locator('.blank:not(.filled)').count())) await sleep(1000);
        continue;
      }
      const ok = await ui.frameWith('#okBtn');
      if (await visible(ok, '#okBtn')) { await sleep(300); await ok.locator('#okBtn').click(); await sleep(1200); continue; }
      await ui.advance(); await sleep(600);
    }
    const t = await ui.waitText(/學會了 \d+ 個字（一共 \d+ 個）/, 5000);
    const learned = +t.match(/學會了 (\d+) 個字/)[1];
    const core = +t.match(/一共 (\d+) 個/)[1];
    if (mode === 'right') assert(learned === core && explains === 0 && reviews === 0, `全對：學會 ${learned}/${core}，解釋 ${explains}、複習 ${reviews}`);
    if (mode === 'wrong') assert(explains === core && reviews === core && learned === core, `全錯一次：解釋 ${explains}、複習 ${reviews}、學會 ${learned}/${core}`);
    await ui.advance();
    const t2 = await ui.waitText(/背誦拿到 \d 顆星/, 8000);
    assert(/背誦拿到 3 顆星/.test(t2), '背誦三關全過拿 3 顆星');
    assert(ui.errors.length === 0, '沒有頁面例外 ' + ui.errors.join(';'));
  } catch (e) { await ui.page.screenshot({ path: `dist/play-${mode}-fail.png` }); throw e; }
  finally { await ui.close(); s.kill(); }
}
if (which === 'all' || which === 'right') await run('right');
if (which === 'all' || which === 'wrong') await run('wrong');
