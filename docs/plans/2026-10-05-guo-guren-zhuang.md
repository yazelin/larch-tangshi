# 唐詩系列〈過故人莊〉實作計劃

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Larch 上做出〈過故人莊〉互動教材（VN＋自製插件 tangshi-kit），本機試玩三條路徑全過，推上 Larch 等作者發佈。

**Architecture:** 劇本寫在 `poems/guo-guren-zhuang/script.md`、生字資料在 `vocab.json`；`src/build.py` 讀兩者組出 `dist/project.json`（對話卡＋插件卡＋有條件連線）。插件 tangshi-kit 四種卡都是單檔 HTML，內容全從卡片參數傳入。`src/push.py` 照《起跑總在開始前》的做法：快照、上傳、整包 PUT、讀回比對。

**Tech Stack:** Python 3 標準庫（建置、檢查、推送）、純 HTML/JS 插件卡、Playwright（借 `~/larch-preview/node_modules`）、`~/larch-preview/serve.py` 本機播放器、Larch agent API、larch-tts-bridge（.11:8072）配生字音。

**Spec:** `docs/specs/2026-10-05-design.md`

## Global Constraints

- 玩家是小學三年級；每個生字有注音與發音。
- 全程 12～15 分鐘；每一條路徑都要走得到結局，答錯不會卡住。
- 插件裡不寫死任何一首詩的內容，全部從卡片參數傳入。
- 插件卡拿不到麥克風，不做語音辨識。
- 插件變數閘門：每張卡會寫的變數必須列在 `pluginWriteVars`，少列會被靜默丟掉。
- 繪圖只用本機 codex 或 .11 codex-image；CG 一律帶在場角色定錨；只把需要作者拍板的圖給作者看。
- 配音並行數寫死 3。破音字替身：斜→霞、郭→鍋、還→孩。
- 推上 Larch 前一定先抓快照；推完比對卡數；發佈由作者在網頁按。
- 授權：程式碼 MIT；角色、劇本、美術、配音 CC BY-NC 4.0。
- 對外中文：全形標點、正體中文、不用 emoji、不用破折號、不用「而是」句型；交稿前跑 `speak-tw`。
- repo 是公開的；`assets/uploaded.json`、`snapshots/`、`dist/` 不進版控（`.gitignore`）。

## Review Focus

1. 小朋友連點選項或在翻卡動畫中再點：只能算一次答案，`learned` 不能加兩次。→ Task 4 加測。
2. 同一個字連錯三次再答對：`got_<id>` 要停在 0（第一次答錯），`learned` 加一。→ Task 4 加測。
3. 編輯器預覽不送 `larch:init`：卡片 2 秒後用預設資料自己啟動，不能空白。→ Task 3 加測。
4. iPhone 直式：選項、字塊、按鈕點擊區至少 44px，畫面不出現橫向捲動。→ Task 4、Task 6 加測。
5. 背誦的干擾字塊不能跟該關被遮住的字重複，否則同一格有兩個「對的」字塊。→ Task 6 加測。

---

## 檔案地圖

```
.gitignore
skeleton/project.json          Larch 新專案的空殼（Task 1 抓回）
canon/系列角色.md               兩個主角設定（Task 2）
poems/guo-guren-zhuang/
  考證.md                      唐代田家考證與注音出處（Task 2）
  vocab.json                   23 個生字（Task 2）
  script.md                    劇本（Task 8）
  art/                         正式美術（Task 9）
  audio/vocab/*.mp3            生字發音（Task 10）
assets/placeholder/            佔位圖（Task 7 產生，進版控）
src/
  cards.py                     對話卡、setVariable 卡、連線（Task 1）
  vocab.py                     讀與驗 vocab.json（Task 2）
  script.py                    劇本解析（Task 2）
  variables.py                 變數表（Task 3）
  plugin.py                    tangshi-kit：卡片節點、manifest、單卡測試專案（Task 3）
  plugin/common.js             卡片與 Larch 溝通（Task 3）
  plugin/vocab.html            生字卡（Task 4）
  plugin/follow.html           跟著念（Task 5）
  plugin/order.html            四張圖排順序（Task 6）
  plugin/recite.html           背誦闖關（Task 6）
  art.py                       美術路徑，缺圖退回佔位圖（Task 7）
  build.py                     組 dist/project.json（Task 7）
  push.py                      推上 Larch（Task 1 搬，Task 11 用）
  vocab_audio.py               生字音檔（Task 10）
tests/
  run.py                       極小測試執行器（Task 1）
  check_static.py              靜態檢查（Task 2 起逐步加）
  lib.mjs                      Playwright 共用（Task 1 搬）
  cards.mjs                    單卡測試（Task 3 起逐步加）
  play_all.mjs                 三條全路徑（Task 7）
```

---

### Task 1：骨架、Larch 專案、推送腳本

**Files:**
- Create: `.gitignore`、`skeleton/project.json`、`src/cards.py`、`src/push.py`、`tests/run.py`、`tests/lib.mjs`、`tests/check_static.py`
- Test: `tests/check_static.py`

**Interfaces:**
- Produces: `cards.dialogue(id, title, lines, bg='', start=False) -> dict`（lines 元素為字串或 `(講者, 文字)`）、`cards.setvar(id, title, ops) -> dict`、`cards.link(board, a, b, handle=None, cond=None)`（`cond=(變數, 運算子, 值)`）、`tests/run.py` 的 `@test` 裝飾器與 `main()`。

- [ ] **Step 1：建 Larch 專案並抓回空殼**

用 MCP 工具 `larch_create_project`，名稱「唐詩小旅行：過故人莊」。記下回傳的 `project-…` id。然後：

```bash
cd ~/larch-tangshi
python3 ~/larch-preview/serve.py --project <project-id>   # 會存一份 JSON，看輸出的路徑
cp <輸出的 JSON 路徑> skeleton/project.json   # 複製完關掉 serve
```

- [ ] **Step 2：`.gitignore`**

```
dist/
snapshots/
assets/uploaded.json
__pycache__/
```

- [ ] **Step 3：寫測試執行器 `tests/run.py`**

```python
"""極小測試執行器：@test 收集，main() 逐一跑，失敗印出並以退出碼 1 結束。"""
import sys, traceback
TESTS = []
def test(f): TESTS.append(f); return f
def main():
    bad = 0
    for f in TESTS:
        try: f(); print('ok  ', f.__name__)
        except Exception:
            bad += 1; print('FAIL', f.__name__); traceback.print_exc()
    print(f'{len(TESTS) - bad}/{len(TESTS)} 通過')
    sys.exit(1 if bad else 0)
```

- [ ] **Step 4：寫失敗的測試 `tests/check_static.py`**

```python
"""靜態檢查：python3 tests/check_static.py"""
import json, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
from run import test, main

@test
def link_with_condition():
    import cards
    b = {'edges': []}
    cards.link(b, 'a', 'b', cond=('last_ok', 'eq', False))
    c = b['edges'][0]['data']['condition']
    assert c['variable'] == 'last_ok' and c['value'] is False and c['conditions'][0]['op'] == 'eq', c

@test
def setvar_card():
    import cards
    n = cards.setvar('h1', '跳', [{'variable': 'hop', 'op': 'set', 'value': 1}])
    assert n['data']['type'] == 'setVariable' and n['data']['variableOps'][0]['variable'] == 'hop'

if __name__ == '__main__': main()
```

- [ ] **Step 5：跑測試確認失敗**

Run: `python3 tests/check_static.py`
Expected: FAIL（`ModuleNotFoundError: No module named 'cards'`）

- [ ] **Step 6：寫 `src/cards.py`**

```python
"""白板卡片節點：對話卡、setVariable 卡、連線（可帶條件）。"""
_x = [0]


def _pos():
    _x[0] += 1
    return {'x': (_x[0] % 8) * 360, 'y': (_x[0] // 8) * 260}


def dialogue(id, title, lines, bg='', start=False):
    """lines：字串（旁白）或 (講者, 文字)。"""
    dl = []
    for i, l in enumerate(lines):
        sp, tx = l if isinstance(l, tuple) else ('', l)
        dl.append({'id': f'{id}-l{i}', 'speaker': sp, 'text': tx})
    data = {'type': 'dialogue', 'title': title, 'speaker': dl[0]['speaker'], 'text': dl[0]['text'],
            'dialogueLines': dl, 'stage': {'actors': []}}
    if bg: data['background'] = bg
    if start: data['start'] = True
    return {'id': id, 'type': 'story', 'position': _pos(), 'data': data}


def setvar(id, title, ops):
    return {'id': id, 'type': 'story', 'position': _pos(),
            'data': {'type': 'setVariable', 'title': title, 'text': '', 'variableOps': ops}}


def link(board, a, b, handle=None, cond=None):
    e = {'id': f'{a}--{b}', 'source': a, 'target': b, 'sourceHandle': handle or 'right', 'targetHandle': 'left'}
    if cond:
        var, op, val = cond
        e['data'] = {'condition': {'kind': 'variable', 'op': op, 'variable': var, 'value': val, 'match': 'all',
                                   'valueSource': 'value',
                                   'conditions': [{'id': f'c-{a}-{b}', 'op': op, 'variable': var, 'value': val,
                                                   'valueSource': 'value'}]}}
    board['edges'].append(e)
```

- [ ] **Step 7：跑測試確認通過**

Run: `python3 tests/check_static.py`
Expected: `2/2 通過`

- [ ] **Step 8：搬 `tests/lib.mjs` 與 `src/push.py`**

```bash
cp ~/larch-start-line/tests/lib.mjs tests/lib.mjs
cp ~/larch-start-line/src/push.py src/push.py
```

`src/push.py` 改四處：

```python
GENERATED_PLUGINS = ('tangshi-kit',)
MIME = {'.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.mp3': 'audio/mpeg'}
```

`merge_settings` 換成（這個作品沒有 RPG）：

```python
def merge_settings(online, built):
    """以線上設定為底，只覆寫產生器負責的鍵：自製插件、封面、縮圖、stageFit。作者在網頁改的其他設定保留。"""
    m = json.loads(json.dumps(online or {}))
    plugins = m.setdefault('plugins', {})
    for k in GENERATED_PLUGINS:
        plugins[k] = built['plugins'][k]
    for k in GENERATED_KEYS:
        if k in built: m[k] = built[k]
    return m

GENERATED_KEYS = ('titleCoverImage', 'projectThumbnail', 'stageFit', 'keepActorsInFrame', 'cgGalleryEnabled')
```

`upload_all` 裡的 `'name': 'start-line_' + …` 改成 `'tangshi_' + …`，`'category'` 改成 `'audio' if f.suffix == '.mp3' else 'image'`；`main` 裡讀回比對的 `'start-line' in back['settings']['plugins']` 改成 `'tangshi-kit'`，並刪掉 `pluginCardId == 'map'` 那段事件數比對。`tests/lib.mjs` 不用改。

- [ ] **Step 9：Commit**

```bash
git add .gitignore skeleton/project.json src/cards.py src/push.py tests/run.py tests/lib.mjs tests/check_static.py
git commit -m "chore: 骨架、Larch 專案空殼、推送腳本"
```

---

### Task 2：正典、生字資料、劇本解析

**Files:**
- Create: `canon/系列角色.md`、`poems/guo-guren-zhuang/考證.md`、`poems/guo-guren-zhuang/vocab.json`、`src/vocab.py`、`src/script.py`
- Modify: `tests/check_static.py`

**Interfaces:**
- Produces:
  - `vocab.POEM = '故人具雞黍，邀我至田家。綠樹村邊合，青山郭外斜。開軒面場圃，把酒話桑麻。待到重陽日，還來就菊花。'`
  - `vocab.LINES -> list[str]`（八句，每句五字，不含標點）
  - `vocab.load(poem='guo-guren-zhuang') -> list[dict]`；每筆鍵：`id`（ASCII，變數名用）、`word`、`zhuyin`（以空白分隔，每字一組）、`meaning`、`core`（bool）、`tts`（送配音的字，預設同 `word`）
  - `vocab.problems(entries) -> list[str]`
  - `script.parse(text) -> {'scenes': [...], 'explain': {word: [(講者, 文字)]}}`；scene 為 `{'id', 'title', 'bg', 'items'}`，item 為 `{'kind': 'line', 'speaker', 'text'}`、`{'kind': 'vocab', 'word'}`、`{'kind': 'follow', 'pair': int}`（0～3，第幾聯）、`{'kind': 'order'}`、`{'kind': 'review'}`、`{'kind': 'recite'}`、`{'kind': 'summary'}`
  - `script.load(poem='guo-guren-zhuang') -> dict`

- [ ] **Step 1：寫 `canon/系列角色.md`**

兩個主角的名字、年級、個性、口頭禪、外觀（髮型、衣服顏色、身高對比）、在唐朝怎麼被稱呼。名字與性別在這一步定案（暫名阿禾、小樂），寫好後**停下來給作者看**，作者確認才往下。

- [ ] **Step 2：寫 `poems/guo-guren-zhuang/考證.md`**

每一條都附出處（網址或書名頁碼），至少涵蓋：黍是什麼作物、長相與顏色（黃色小米粒）；雞黍作為待客飯菜的典故（《論語．微子》）；郭的意思；軒、場、圃各指什麼；桑與麻的用途（養蠶織絲、織布）；重陽的習俗（登高、賞菊、菊花酒）；唐代農家房舍樣貌；孟浩然生平與這首詩的背景。另外逐字列出 23 個生字的注音，以教育部《重編國語辭典修訂本》查到的為準，附詞條網址；「斜」讀 ㄒㄧㄚˊ（押韻傳統讀法）、「場」在「場圃」讀 ㄔㄤˊ、「還」讀 ㄏㄞˊ 這三條要寫出依據。

- [ ] **Step 3：寫 `poems/guo-guren-zhuang/vocab.json`**

注音以 Step 2 查到的為準；下面是初稿，與辭典不符時改辭典的值。

```json
[
 {"id": "guo4", "word": "過", "zhuyin": "ㄍㄨㄛˋ", "meaning": "拜訪", "core": false},
 {"id": "guren", "word": "故人", "zhuyin": "ㄍㄨˋ ㄖㄣˊ", "meaning": "老朋友", "core": false},
 {"id": "zhuang", "word": "莊", "zhuyin": "ㄓㄨㄤ", "meaning": "農家住的村莊", "core": false},
 {"id": "ju", "word": "具", "zhuyin": "ㄐㄩˋ", "meaning": "準備", "core": false},
 {"id": "jishu", "word": "雞黍", "zhuyin": "ㄐㄧ ㄕㄨˇ", "meaning": "雞肉和黃米飯，招待客人的飯菜", "core": true},
 {"id": "yao", "word": "邀", "zhuyin": "ㄧㄠ", "meaning": "邀請", "core": true},
 {"id": "zhi", "word": "至", "zhuyin": "ㄓˋ", "meaning": "到", "core": false},
 {"id": "tianjia", "word": "田家", "zhuyin": "ㄊㄧㄢˊ ㄐㄧㄚ", "meaning": "種田的人家", "core": false},
 {"id": "he", "word": "合", "zhuyin": "ㄏㄜˊ", "meaning": "圍繞起來", "core": true},
 {"id": "guo1", "word": "郭", "zhuyin": "ㄍㄨㄛ", "meaning": "城牆外面再圍的一道牆", "core": true, "tts": "鍋"},
 {"id": "xia", "word": "斜", "zhuyin": "ㄒㄧㄚˊ", "meaning": "斜斜地橫在那裡", "core": true, "tts": "霞"},
 {"id": "xuan", "word": "軒", "zhuyin": "ㄒㄩㄢ", "meaning": "窗戶", "core": true},
 {"id": "mian", "word": "面", "zhuyin": "ㄇㄧㄢˋ", "meaning": "面對", "core": false},
 {"id": "chang", "word": "場", "zhuyin": "ㄔㄤˊ", "meaning": "曬穀、打穀的空地", "core": true, "tts": "腸"},
 {"id": "pu", "word": "圃", "zhuyin": "ㄆㄨˇ", "meaning": "菜園", "core": false},
 {"id": "ba", "word": "把", "zhuyin": "ㄅㄚˇ", "meaning": "拿著", "core": true},
 {"id": "hua", "word": "話", "zhuyin": "ㄏㄨㄚˋ", "meaning": "聊天、談論", "core": true},
 {"id": "sangma", "word": "桑麻", "zhuyin": "ㄙㄤ ㄇㄚˊ", "meaning": "桑樹和麻，代表種田養蠶的農事", "core": true},
 {"id": "daidao", "word": "待到", "zhuyin": "ㄉㄞˋ ㄉㄠˋ", "meaning": "等到", "core": false},
 {"id": "chongyang", "word": "重陽", "zhuyin": "ㄔㄨㄥˊ ㄧㄤˊ", "meaning": "農曆九月九日，賞菊、登高的節日", "core": true},
 {"id": "hailai", "word": "還來", "zhuyin": "ㄏㄞˊ ㄌㄞˊ", "meaning": "再來", "core": false, "tts": "孩來"},
 {"id": "jiu", "word": "就", "zhuyin": "ㄐㄧㄡˋ", "meaning": "靠近，去欣賞", "core": true},
 {"id": "juhua", "word": "菊花", "zhuyin": "ㄐㄩˊ ㄏㄨㄚ", "meaning": "秋天開的花，重陽節要賞", "core": false}
]
```

- [ ] **Step 4：寫失敗的測試（加進 `tests/check_static.py`，放在 `if __name__` 之前）**

```python
@test
def vocab_ok():
    import vocab
    v = vocab.load()
    assert len(v) == 23 and sum(e['core'] for e in v) == 12, (len(v), sum(e['core'] for e in v))
    assert vocab.problems(v) == [], vocab.problems(v)

@test
def vocab_problems_catch():
    import vocab
    bad = [{'id': 'x-1', 'word': '雞黍', 'zhuyin': 'ㄐㄧ', 'meaning': '', 'core': True},
           {'id': 'y', 'word': '不在詩裡', 'zhuyin': 'ㄅ ㄅ ㄅ ㄅ', 'meaning': '甲', 'core': False}]
    p = vocab.problems(bad)
    assert any('x-1' in s and 'id' in s for s in p) and any('注音' in s for s in p) \
        and any('meaning' in s for s in p) and any('不在詩裡' in s for s in p), p

@test
def poem_lines():
    import vocab
    assert vocab.LINES[5] == '把酒話桑麻' and len(vocab.LINES) == 8 and all(len(l) == 5 for l in vocab.LINES)

SAMPLE = '''# s1 故人具雞黍 | bg=gate
孟浩然：有人送信來了。
旁白：門口站著一個孩子。
@生字 雞黍
@跟念 0
# explain
## 雞黍
故人：你看，這一粒一粒黃黃的就是黍。
'''

@test
def script_parse():
    import script
    s = script.parse(SAMPLE)
    sc = s['scenes'][0]
    assert (sc['id'], sc['title'], sc['bg']) == ('s1', '故人具雞黍', 'gate'), sc
    assert sc['items'][0] == {'kind': 'line', 'speaker': '孟浩然', 'text': '有人送信來了。'}
    assert sc['items'][1]['speaker'] == '旁白'
    assert sc['items'][2] == {'kind': 'vocab', 'word': '雞黍'} and sc['items'][3] == {'kind': 'follow', 'pair': 0}
    assert s['explain']['雞黍'] == [('故人', '你看，這一粒一粒黃黃的就是黍。')]

@test
def script_bad_directive():
    import script
    try: script.parse('# s1 x\n@不存在 1\n')
    except ValueError as e: assert '第 2 行' in str(e), e; return
    raise AssertionError('未知指令應該 raise ValueError')
```

- [ ] **Step 5：跑測試確認失敗**

Run: `python3 tests/check_static.py`
Expected: 新的五個 FAIL（`No module named 'vocab'`／`'script'`）

- [ ] **Step 6：寫 `src/vocab.py`**

```python
"""生字資料：讀 poems/<詩>/vocab.json 並檢查。"""
import json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
POEM = '故人具雞黍，邀我至田家。綠樹村邊合，青山郭外斜。開軒面場圃，把酒話桑麻。待到重陽日，還來就菊花。'
LINES = re.findall(r'[^，。]+', POEM)


def load(poem='guo-guren-zhuang'):
    entries = json.loads((ROOT / 'poems' / poem / 'vocab.json').read_text())
    for e in entries: e.setdefault('tts', e['word'])
    return entries


def problems(entries):
    out, seen = [], set()
    for e in entries:
        w = e['word']
        if not re.fullmatch(r'[a-z][a-z0-9]*', e['id']): out.append(f'{w}: id {e["id"]!r} 只能用小寫英數')
        if e['id'] in seen: out.append(f'{w}: id 重複')
        seen.add(e['id'])
        if len(e['zhuyin'].split()) != len(w): out.append(f'{w}: 注音組數 {len(e["zhuyin"].split())} ≠ 字數 {len(w)}')
        if not e.get('meaning'): out.append(f'{w}: meaning 空白')
        if w not in POEM: out.append(f'{w}: 不在詩裡')
    return out
```

- [ ] **Step 7：寫 `src/script.py`**

```python
"""劇本解析。格式：
# <場景id> <標題> | bg=<背景鍵>     開新場景（bg 可省）
講者：台詞                          台詞；沒有「：」的行算旁白
@生字 <詞>  @跟念 <0-3>  @排圖  @複習  @背誦  @結算
# explain 之後用 ## <詞> 分段，寫答錯時的解釋台詞
空行與 <!-- --> 註解略過。
"""
import pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
SIMPLE = {'@排圖': 'order', '@複習': 'review', '@背誦': 'recite', '@結算': 'summary'}


def parse(text):
    scenes, explain, cur, word = [], {}, None, None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('<!--'): continue
        if line.startswith('# '):
            head, _, opt = line[2:].partition('|')
            sid, _, title = head.strip().partition(' ')
            if sid == 'explain': cur = 'explain'; continue
            bg = re.search(r'bg=(\S+)', opt)
            cur = {'id': sid, 'title': title.strip(), 'bg': bg.group(1) if bg else '', 'items': []}
            scenes.append(cur); continue
        if cur == 'explain':
            if line.startswith('## '): word = line[3:].strip(); explain[word] = []; continue
            sp, _, tx = line.partition('：')
            explain[word].append((sp, tx) if tx else ('', sp)); continue
        if cur is None: raise ValueError(f'第 {n} 行：還沒有場景標題')
        if line.startswith('@'):
            cmd, _, arg = line.partition(' ')
            if cmd == '@生字': cur['items'].append({'kind': 'vocab', 'word': arg.strip()})
            elif cmd == '@跟念': cur['items'].append({'kind': 'follow', 'pair': int(arg)})
            elif cmd in SIMPLE: cur['items'].append({'kind': SIMPLE[cmd]})
            else: raise ValueError(f'第 {n} 行：不認得的指令 {cmd}')
            continue
        sp, _, tx = line.partition('：')
        cur['items'].append({'kind': 'line', 'speaker': sp if tx else '旁白', 'text': tx or sp})
    return {'scenes': scenes, 'explain': explain}


def load(poem='guo-guren-zhuang'):
    return parse((ROOT / 'poems' / poem / 'script.md').read_text())
```

- [ ] **Step 8：跑測試確認通過**

Run: `python3 tests/check_static.py`
Expected: `7/7 通過`

- [ ] **Step 9：Commit**

```bash
git add canon poems/guo-guren-zhuang/考證.md poems/guo-guren-zhuang/vocab.json src/vocab.py src/script.py tests/check_static.py
git commit -m "feat: 系列角色、考證、生字資料與劇本解析"
```

---

### Task 3：插件骨架 tangshi-kit（common.js、變數、節點、單卡測試專案）

**Files:**
- Create: `src/variables.py`、`src/plugin.py`、`src/plugin/common.js`、`tests/cards.mjs`
- Modify: `tests/check_static.py`

**Interfaces:**
- Consumes: `cards._pos`、`cards.dialogue`、`cards.link`、`vocab.load`
- Produces:
  - `variables.VARS: dict[name -> (type, default, label)]`，含 `last_ok`(boolean, False)、`learned`(number, 0)、`stars`(number, 0)、`hop`(number, 0)，以及每個核心字的 `got_<id>`(number, -1)。`variables.project_variables() -> list[dict]`。
  - `plugin.PLUGIN_ID = 'tangshi-kit'`、`plugin.CARDS: dict[card_id -> {'name', 'presentation'}]`，card_id 為 `vocab`、`follow`、`order`、`recite`。
  - `plugin.card_node(card_id, node_id, script: dict, read: list, write: list) -> dict`
  - `plugin.settings_entry() -> dict`、`plugin.manifest() -> dict`、`plugin.html(card_id) -> str`
  - `plugin.test_project(card_id, script, read, write, preset=None) -> dict`；`python3 src/plugin.py --test <card_id>` 用 `plugin.SAMPLES[card_id]` 產 `dist/test-<card_id>.json`
  - 卡片 JS：`L.onInit(fn(script, vars))`、`L.set(name, value)`、`L.get(name, dflt)`、`L.done()`、`L.play(url, from=0, dur=0) -> Audio`

- [ ] **Step 1：寫失敗的測試（加進 `tests/check_static.py`）**

```python
@test
def variables_cover_core():
    import variables, vocab
    for e in vocab.load():
        if e['core']: assert f"got_{e['id']}" in variables.VARS, e['id']
    for k in ('last_ok', 'learned', 'stars', 'hop'): assert k in variables.VARS

@test
def card_node_gate_lists():
    import plugin
    n = plugin.card_node('vocab', 'n1', {'word': '郭'}, read=['got_guo1', 'learned'], write=['got_guo1', 'learned', 'last_ok'])
    d = n['data']
    assert d['pluginId'] == 'tangshi-kit' and d['pluginCardId'] == 'vocab'
    assert d['pluginWriteVars'] == ['got_guo1', 'learned', 'last_ok'] and d['pluginFrame']['showButton'] is False
    assert '"word": "郭"' in d['pluginValues']['script'] and 'common.js' not in d['pluginHtml']
```

- [ ] **Step 2：跑測試確認失敗**

Run: `python3 tests/check_static.py`
Expected: 兩個新測試 FAIL（`No module named 'variables'`）

- [ ] **Step 3：寫 `src/variables.py`**

```python
"""全專案變數只在這裡定義：名字 → (型別, 預設值, 標籤)。got_<id>：-1 沒看過、0 第一次答錯、1 第一次答對、2 複習時答對。"""
import vocab

VARS = {
    'last_ok': ('boolean', False, '剛才那題答對'),
    'learned': ('number', 0, '學會的字數'),
    'stars': ('number', 0, '背誦星星'),
    'hop': ('number', 0, '複習進度'),
}
for _e in vocab.load():
    if _e['core']: VARS[f"got_{_e['id']}"] = ('number', -1, f"生字：{_e['word']}")


def project_variables():
    return [{'id': k, 'name': k, 'label': lab, 'type': t, 'defaultValue': d} for k, (t, d, lab) in VARS.items()]
```

- [ ] **Step 4：寫 `src/plugin/common.js`**

```js
/* 卡片共用：跟 Larch 溝通。編輯器預覽不送 init，2 秒後用 window.SAMPLE 自己啟動。 */
var L = (function () {
  var initFns = [], vars = {}, started = false, finished = false;
  function start(script, v) {
    if (started) return; started = true; vars = v || {};
    initFns.forEach(function (f) { f(script, vars); });
  }
  addEventListener('message', function (e) {
    var d = e.data; if (!d || d.type !== 'larch:init') return;
    var s = {}; try { s = JSON.parse((d.values || {}).script || '{}'); } catch (err) {}
    start(s, d.variables);
  });
  parent.postMessage({ type: 'larch:ready' }, '*');
  setTimeout(function () { start(window.SAMPLE || {}, {}); }, 2000);
  return {
    onInit: function (f) { initFns.push(f); },
    set: function (n, v) { vars[n] = v; parent.postMessage({ type: 'larch:set', name: n, value: v }, '*'); },
    get: function (n, dflt) { return (n in vars && vars[n] !== '' && vars[n] != null) ? vars[n] : dflt; },
    done: function () { if (finished) return; finished = true; parent.postMessage({ type: 'larch:complete' }, '*'); },
    play: function (url, from, dur) {
      if (!url) return null;
      var a = new Audio(url); a.currentTime = from || 0; a.play().catch(function () {});
      if (dur) setTimeout(function () { a.pause(); }, dur * 1000);
      return a;
    }
  };
})();
```

- [ ] **Step 5：寫 `src/plugin.py`**

```python
"""自製插件 tangshi-kit：生字、跟著念、排圖、背誦四張卡。產卡片節點、settings.plugins、manifest 與單卡測試專案。

    python3 src/plugin.py --test <card_id>   # 產 dist/test-<card_id>.json
"""
import json, pathlib, sys
import cards, variables

HERE = pathlib.Path(__file__).resolve().parent / 'plugin'
ROOT = HERE.parent.parent
PLUGIN_ID, VERSION, NAME, COLOR = 'tangshi-kit', '1.0.0', '唐詩小旅行', '#2f6b4f'
CARDS = {
    'vocab': {'name': '生字卡', 'presentation': 'fullscreen'},
    'follow': {'name': '跟著念', 'presentation': 'fullscreen'},
    'order': {'name': '四張圖排順序', 'presentation': 'fullscreen'},
    'recite': {'name': '背誦闖關', 'presentation': 'fullscreen'},
}
# 單卡測試用的資料；卡片 HTML 內的 window.SAMPLE 也用同一份（編輯器預覽的預設值）
SAMPLES = {}


def html(card_id):
    src = (HERE / f'{card_id}.html').read_text()
    sample = '<script>window.SAMPLE=' + json.dumps(SAMPLES.get(card_id, {}).get('script', {}), ensure_ascii=False) + '</script>'
    return src.replace('<script src="common.js"></script>', sample + '<script>' + (HERE / 'common.js').read_text() + '</script>')


def card_node(card_id, node_id, script, read, write):
    c = CARDS[card_id]
    return {'id': node_id, 'type': 'story', 'position': cards._pos(), 'data': {
        'type': 'plugin', 'title': c['name'], 'text': '', 'pluginId': PLUGIN_ID, 'pluginCardId': card_id,
        'pluginName': NAME, 'pluginCardName': c['name'], 'pluginVersion': VERSION, 'pluginIcon': 'book',
        'pluginColor': COLOR, 'pluginHtml': html(card_id), 'pluginPresentation': c['presentation'],
        'pluginValues': {'script': json.dumps(script, ensure_ascii=False)}, 'pluginAssets': [],
        'pluginReadVars': list(read), 'pluginWriteVars': list(write), 'pluginSkippable': False,
        'pluginFrame': {'showTitle': False, 'showButton': False}, 'platforms': ['web']}}


def settings_entry():
    return {'enabled': True, 'playback': {'version': VERSION, 'permissions': ['variables:read'], 'defaults': {}, 'huds': []}}


def manifest():
    """給 larch_save_plugin_draft 的完整 manifest。"""
    return {'id': PLUGIN_ID, 'name': NAME, 'version': VERSION, 'author': '林亞澤',
            'description': '唐詩教材用：生字卡、跟著念、四張圖排順序、背誦闖關。內容全由卡片參數 script（JSON）傳入。',
            'categories': ['card'], 'icon': 'book',
            'permissions': ['variables:read', 'variables:write', 'assets:read', 'flow:control'],
            'cards': [{'id': k, 'name': c['name'], 'description': c['name'], 'icon': 'book', 'color': COLOR,
                       'presentation': c['presentation'],
                       'fields': [{'key': 'script', 'kind': 'longText', 'label': '內容（JSON）'}],
                       'html': html(k)} for k, c in CARDS.items()], 'huds': []}


def test_project(card_id, script, read, write, preset=None):
    import build
    p = build.load_skeleton()
    b = p['boards'][0]
    b['nodes'], b['edges'] = [], []
    p['nodes'], p['edges'] = b['nodes'], b['edges']
    p['variables'] = variables.project_variables()
    for v in p['variables']:
        if v['name'] in (preset or {}): v['defaultValue'] = preset[v['name']]
    p['settings']['plugins'][PLUGIN_ID] = settings_entry()
    b['nodes'].append(cards.dialogue('t-start', '測試開始', ['測試：' + card_id], start=True))
    b['nodes'].append(card_node(card_id, 't-card', script, read, write))
    shown = ' '.join(f'{k}={{{{{k}}}}}' for k in write)
    b['nodes'].append(cards.dialogue('t-result', '結果', ['RESULT ' + shown]))
    cards.link(b, 't-start', 't-card'); cards.link(b, 't-card', 't-result')
    return p


if __name__ == '__main__':
    if sys.argv[1:2] == ['--test']:
        import build
        cid = sys.argv[2]
        s = SAMPLES[cid]
        out = ROOT / f'dist/test-{cid}.json'
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(test_project(cid, s['script'], s['read'], s['write'], s.get('preset')), ensure_ascii=False))
        build.mirror_assets(out.parent / 'assets')
        print('wrote', out)
```

`SAMPLES` 的每一筆形狀是 `{'script': {...}, 'read': [...], 'write': [...], 'preset': {...}}`，由 Task 4～6 各自加入。

- [ ] **Step 6：跑測試確認通過**

Run: `python3 tests/check_static.py`
Expected: 全部通過（`card_node_gate_lists` 需要 `src/plugin/vocab.html` 存在：先放一個只有 `<script src="common.js"></script>` 的空殼，Task 4 再寫滿）

- [ ] **Step 7：寫 `tests/cards.mjs` 的共用部分與「沒有 init 也會啟動」測試**

```js
// 單卡測試：node tests/cards.mjs [card_id]。每張卡先 python3 src/plugin.py --test <id>
import { serve, open, assert, sleep } from './lib.mjs';
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';

const only = process.argv[2];
const TESTS = {};
export function cardTest(id, fn) { TESTS[id] = fn; }

async function withCard(id, fn, opts) {
  execFileSync('python3', ['src/plugin.py', '--test', id], { stdio: 'inherit' });
  const s = await serve(`dist/test-${id}.json`);
  const ui = await open(s.base, opts);
  try {
    await ui.clickText('開始遊戲').catch(() => {});
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

for (const [id, fn] of Object.entries(TESTS)) if (!only || only === id) await fn(withCard, noInit);
```

各卡的測試在 Task 4～6 用 `cardTest(id, async (withCard, noInit) => …)` 寫在 `cards.mjs` 末段、`for` 迴圈之前。

- [ ] **Step 8：Commit**

```bash
git add src/variables.py src/plugin.py src/plugin/common.js src/plugin/vocab.html tests/check_static.py tests/cards.mjs
git commit -m "feat: tangshi-kit 插件骨架與變數表"
```

---

### Task 4：生字卡 vocab.html

**Files:**
- Modify: `src/plugin/vocab.html`、`src/plugin.py`（`SAMPLES['vocab']`）、`tests/cards.mjs`

**Interfaces:**
- Consumes: `L.onInit`、`L.set`、`L.get`、`L.done`、`L.play`
- Produces: 卡片 script 形狀（build.py 照這個產）：

```json
{"word": "雞黍", "zhuyin": "ㄐㄧ ㄕㄨˇ", "meaning": "…", "img": "<url>", "audio": "<url>",
 "quiz": true, "retry": true, "gotVar": "got_jishu", "review": false,
 "ask": "「雞黍」是什麼意思？",
 "options": [{"img": "<url>", "label": "雞和黃米飯", "ok": true}, {"img": "<url>", "label": "…", "ok": false}, {"img": "<url>", "label": "…", "ok": false}]}
```

- 行為：
  - `quiz: false`：顯示字、注音、圖、解釋，點字播音，按「好」→ `L.done()`。
  - `quiz: true`：先顯示字與注音（不顯示解釋），三個選項。第一次作答之後鎖住所有選項。
    - 答對：`last_ok=true`；若 `gotVar` 目前是 -1 → 設 1；若是 0 → 設 2（`review: true` 時）；`gotVar` 從 -1 或 0 變成 1 或 2 時 `learned += 1`。翻面顯示解釋，按「好」→ `L.done()`。
    - 答錯：`last_ok=false`；若 `gotVar` 是 -1 → 設 0。`retry: true` 時選項搖一下，0.8 秒後 `L.done()`（劇情走解釋分支，再回來重答）。`retry: false`（複習時）直接翻面顯示正確答案，按「好」→ `L.done()`。
  - 每個選項是 `<button data-ok="1|0">`，最小 44×44px。

- [ ] **Step 1：寫失敗的測試（加進 `tests/cards.mjs`）**

```js
cardTest('vocab', async (withCard, noInit) => {
  await noInit('vocab', 'button[data-ok]');
  const result = async ui => (await ui.waitText(/RESULT/)).match(/RESULT.*/)[0];
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
```

`withCard(id, fn, opts, { preset, patch } = {})`：有 `preset` 或 `patch` 時改跑 `python3 src/plugin.py --test <id> --preset '<json>' --patch '<json>'`。`plugin.py` 的 `__main__` 讀這兩個參數：`preset` 覆寫 `SAMPLES[cid]['preset']`，`patch` 用 `dict.update` 蓋在 `SAMPLES[cid]['script']` 上。`tests/cards.mjs` 的 `withCard` 照此改寫：

```js
async function withCard(id, fn, opts, { preset, patch } = {}) {
  const args = ['src/plugin.py', '--test', id];
  if (preset) args.push('--preset', JSON.stringify(preset));
  if (patch) args.push('--patch', JSON.stringify(patch));
  execFileSync('python3', args, { stdio: 'inherit' });
  // 其餘同 Task 3
```

`src/plugin.py` 的 `__main__` 改成：

```python
if __name__ == '__main__':
    if sys.argv[1:2] == ['--test']:
        import build, copy
        cid = sys.argv[2]
        s = copy.deepcopy(SAMPLES[cid])
        args = dict(zip(sys.argv[3::2], sys.argv[4::2]))
        if '--preset' in args: s['preset'] = json.loads(args['--preset'])
        if '--patch' in args: s['script'].update(json.loads(args['--patch']))
        out = ROOT / f'dist/test-{cid}.json'
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(test_project(cid, s['script'], s['read'], s['write'], s.get('preset')), ensure_ascii=False))
        build.mirror_assets(out.parent / 'assets')
        print('wrote', out)
`````

第三段要用 preset `got_jishu=0`：`withCard` 加第三個參數 `preset`，存在時改跑 `python3 src/plugin.py --test vocab --preset '{"got_jishu":0}'`；`plugin.py` 的 `__main__` 讀這個參數並覆寫 `SAMPLES[cid]['preset']`。上面第三段把 `undefined` 換成 `{ got_jishu: 0 }`，`withCard(id, fn, opts, preset)` 的簽名照此改，第四段改成 `withCard('vocab', fn, { mobile: true })`。

- [ ] **Step 2：加 `SAMPLES['vocab']`（`src/plugin.py`）**

```python
SAMPLES['vocab'] = {
    'script': {'word': '雞黍', 'zhuyin': 'ㄐㄧ ㄕㄨˇ', 'meaning': '雞肉和黃米飯，招待客人的飯菜',
               'img': '/files/assets/placeholder/vocab.png', 'audio': '', 'quiz': True, 'retry': True,
               'gotVar': 'got_jishu', 'review': False, 'ask': '「雞黍」是什麼意思？',
               'options': [{'img': '/files/assets/placeholder/vocab.png', 'label': '雞肉和黃米飯', 'ok': True},
                           {'img': '/files/assets/placeholder/vocab.png', 'label': '一隻小雞', 'ok': False},
                           {'img': '/files/assets/placeholder/vocab.png', 'label': '白米飯', 'ok': False}]},
    'read': ['got_jishu', 'learned'], 'write': ['got_jishu', 'learned', 'last_ok']}
```

- [ ] **Step 3：跑測試確認失敗**

Run: `node tests/cards.mjs vocab`
Expected: FAIL（空殼卡找不到 `button[data-ok]`）

- [ ] **Step 4：寫 `src/plugin/vocab.html`**

```html
<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;height:100%;overflow:hidden;background:#fbf3e4;color:#2b2b2b;font-family:"Noto Sans TC",system-ui,sans-serif}
#card{position:absolute;inset:4vh 4vw;display:flex;flex-direction:column;align-items:center;gap:2vh}
#head{display:flex;align-items:center;gap:3vw;cursor:pointer;border:0;background:none;padding:0}
#word{font-family:"LXGW WenKai TC","BiauKai","DFKai-SB",serif;font-size:min(22vw,22vh);line-height:1;color:#2b2b2b}
#zhuyin{writing-mode:vertical-rl;font-size:min(4.5vw,3.6vh);letter-spacing:.2em;color:#6b6257}
#pic{width:min(40vw,26vh);aspect-ratio:1;object-fit:contain}
#ask{font-size:min(5vw,3vh)}
#opts{display:grid;grid-template-columns:repeat(3,1fr);gap:3vw;width:100%;max-width:720px}
#opts button{min-width:44px;min-height:44px;border:3px solid #e2d6bd;border-radius:16px;background:#fff;padding:8px;font:inherit;font-size:min(4vw,2.4vh);display:flex;flex-direction:column;align-items:center;gap:6px;cursor:pointer}
#opts button img{width:100%;aspect-ratio:1;object-fit:contain}
#opts button.right{border-color:#2f6b4f;background:#eaf5e4}
#opts button.wrong{border-color:#c8553d;animation:shake .4s}
@keyframes shake{25%{translate:-8px}75%{translate:8px}}
#meaning{font-size:min(5.5vw,3.4vh);text-align:center;max-width:90%;display:none}
#okBtn{display:none;min-width:120px;min-height:48px;border:0;border-radius:24px;background:#2f6b4f;color:#fff;font:600 min(5vw,3vh) inherit;cursor:pointer}
body.shown #meaning,body.shown #okBtn{display:block}
body.shown #opts,body.shown #ask{display:none}
</style></head>
<body>
<div id="card">
  <button id="head" aria-label="聽發音"><span id="word"></span><span id="zhuyin"></span></button>
  <img id="pic" alt="">
  <div id="ask"></div>
  <div id="opts"></div>
  <div id="meaning"></div>
  <button id="okBtn">好</button>
</div>
<script src="common.js"></script>
<script>
var S = {}, answered = false, $ = function (id) { return document.getElementById(id); };
function show() { document.body.classList.add('shown'); }
function answer(btn, ok) {
  if (answered) return; answered = true;
  var got = L.get(S.gotVar, -1);
  L.set('last_ok', ok);
  if (ok) {
    btn.classList.add('right');
    var next = got === -1 ? 1 : (S.review ? 2 : got);
    if (next !== got) L.set(S.gotVar, next);
    if (got === -1 || (got === 0 && S.review)) L.set('learned', L.get('learned', 0) + 1);
    setTimeout(show, 500);
  } else {
    btn.classList.add('wrong');
    if (got === -1) L.set(S.gotVar, 0);
    if (S.retry) setTimeout(L.done, 800);
    else { var r = document.querySelector('button[data-ok="1"]'); r && r.classList.add('right'); setTimeout(show, 900); }
  }
}
L.onInit(function (s) {
  S = s; document.body.dataset.review = S.review ? '1' : '0';
  $('word').textContent = S.word; $('zhuyin').textContent = S.zhuyin;
  $('pic').src = S.img || ''; $('meaning').textContent = S.word + '：' + S.meaning;
  $('head').onclick = function () { L.play(S.audio); };
  $('okBtn').onclick = function () { L.done(); };
  if (!S.quiz) { show(); return; }
  $('ask').textContent = S.ask;
  (S.options || []).forEach(function (o) {
    var b = document.createElement('button');
    b.dataset.ok = o.ok ? '1' : '0';
    b.innerHTML = '<img alt=""><span></span>'; b.querySelector('img').src = o.img; b.querySelector('span').textContent = o.label;
    b.onclick = function () { answer(b, !!o.ok); };
    $('opts').appendChild(b);
  });
  L.play(S.audio);
});
</script>
</body></html>
```

`learned` 的規則：只有「第一次就答對（-1→1）」或「複習卡答對（0→2）」會加一；主線答錯後重答答對不加，那個字留給複習。這樣每個字最多算一次。

- [ ] **Step 5：跑測試確認通過**

Run: `node tests/cards.mjs vocab`
Expected: 全部 `ok`

- [ ] **Step 6：Commit**

```bash
git add src/plugin/vocab.html src/plugin.py tests/cards.mjs
git commit -m "feat: 生字卡（答題、翻面、複習計分）"
```

---

### Task 5：跟著念 follow.html

**Files:**
- Modify: `src/plugin/follow.html`（新建）、`src/plugin.py`（`SAMPLES['follow']`）、`tests/cards.mjs`

**Interfaces:**
- Produces: script 形狀 `{"lines": ["故人具雞黍", "邀我至田家"], "audio": "<url>", "marks": [0.0, 0.4, …]}`；`marks` 長度等於總字數（10），省略時用音檔長度平均分配。卡片不寫變數。
- 行為：逐字由墨灰變墨黑並放大，對齊 `marks`；音檔播完或沒音檔時 `10 × 0.5` 秒後出現「再念一次」與「好」。點任一字：從該字的 mark 播 0.6 秒。按「好」→ `L.done()`。

- [ ] **Step 1：寫失敗的測試**

```js
cardTest('follow', async (withCard, noInit) => {
  await noInit('follow', '.ch');
  await withCard('follow', async ui => {
    const f = await ui.frameWith('.ch');
    assert(await f.locator('.ch').count() === 10, '十個字');
    await f.locator('#okBtn').waitFor({ state: 'visible', timeout: 12000 });
    assert(await f.locator('.ch.lit').count() === 10, '念完十個字都點亮');
    await f.locator('#okBtn').click();
    await ui.waitText(/RESULT/);
  });
});
```

- [ ] **Step 2：加 `SAMPLES['follow']`**

```python
SAMPLES['follow'] = {'script': {'lines': ['故人具雞黍', '邀我至田家'], 'audio': '', 'marks': []}, 'read': [], 'write': []}
```

- [ ] **Step 3：跑測試確認失敗**

Run: `node tests/cards.mjs follow`
Expected: FAIL（`follow.html` 不存在）

- [ ] **Step 4：寫 `src/plugin/follow.html`**

```html
<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;height:100%;overflow:hidden;background:#fbf3e4;font-family:"Noto Sans TC",system-ui,sans-serif}
#wrap{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5vh}
.row{display:flex;gap:min(3vw,2vh)}
.ch{font-family:"LXGW WenKai TC","BiauKai","DFKai-SB",serif;font-size:min(15vw,12vh);color:#b9ae9c;border:0;background:none;padding:0 2px;min-width:44px;min-height:44px;cursor:pointer;transition:none}
.ch.lit{color:#2b2b2b;scale:1.08}
#bar{display:flex;gap:4vw;visibility:hidden}
#bar button{min-width:120px;min-height:48px;border-radius:24px;font:600 min(5vw,3vh) inherit;cursor:pointer}
#again{border:2px solid #2f6b4f;background:#fff;color:#2f6b4f}
#okBtn{border:0;background:#2f6b4f;color:#fff}
#label{font-size:min(5vw,3vh);color:#6b6257}
</style></head>
<body>
<div id="wrap"><div id="label">跟著念</div><div id="rows"></div><div id="bar"><button id="again">再念一次</button><button id="okBtn">好</button></div></div>
<script src="common.js"></script>
<script>
var S, chars = [], timers = [];
function run() {
  timers.forEach(clearTimeout); timers = [];
  chars.forEach(function (c) { c.classList.remove('lit'); });
  document.getElementById('bar').style.visibility = 'hidden';
  var a = L.play(S.audio);
  function go(marks, total) {
    marks.forEach(function (t, i) { timers.push(setTimeout(function () { chars[i].classList.add('lit'); }, t * 1000)); });
    timers.push(setTimeout(function () { document.getElementById('bar').style.visibility = 'visible'; }, total * 1000));
  }
  var n = chars.length;
  if (S.marks && S.marks.length === n) { go(S.marks, (a && a.duration) || S.marks[n - 1] + 0.8); return; }
  if (a) a.addEventListener('loadedmetadata', function () { var d = a.duration; go(chars.map(function (_, i) { return d * i / n; }), d); });
  else go(chars.map(function (_, i) { return i * 0.5; }), n * 0.5);
}
L.onInit(function (s) {
  S = s;
  var rows = document.getElementById('rows');
  S.lines.forEach(function (line) {
    var r = document.createElement('div'); r.className = 'row';
    line.split('').forEach(function (c) {
      var b = document.createElement('button'); b.className = 'ch'; b.textContent = c;
      var i = chars.length; b.onclick = function () { var m = (S.marks && S.marks[i]) || 0; L.play(S.audio, m, 0.6); };
      chars.push(b); r.appendChild(b);
    });
    rows.appendChild(r);
  });
  document.getElementById('again').onclick = run;
  document.getElementById('okBtn').onclick = function () { L.done(); };
  run();
});
</script>
</body></html>
```

- [ ] **Step 5：跑測試確認通過**

Run: `node tests/cards.mjs follow`
Expected: 全部 `ok`

- [ ] **Step 6：Commit**

```bash
git add src/plugin/follow.html src/plugin.py tests/cards.mjs
git commit -m "feat: 跟著念卡"
```

---

### Task 6：四張圖排順序 order.html、背誦闖關 recite.html

**Files:**
- Create: `src/plugin/order.html`、`src/plugin/recite.html`、`src/recite_plan.py`
- Modify: `src/plugin.py`（兩筆 SAMPLES）、`tests/cards.mjs`、`tests/check_static.py`、`docs/specs/2026-10-05-design.md`（排圖改成點兩張交換）

**Interfaces:**
- Produces:
  - order script：`{"items": [{"img": "<url>", "caption": "故人具雞黍，邀我至田家"}, ×4], "start": [2, 0, 3, 1]}`；`items` 是正確順序，`start` 是開場擺放（`start[i]` 是第 i 格放哪一張）。點一張、再點另一張就交換。四張都在對的位置時顯示「排好了」與「好」→ `L.done()`。每格是 `<button class="slot" data-idx="<張的編號>">`。
  - `recite_plan.plan(lines: list[str], seed: int = 7) -> list[dict]`：三關，每關 `{'hide': [全詩字的索引…], 'tiles': [字…]}`，遮的比例 1/3、2/3、全部（無條件進位）；`tiles` = 遮住的字＋3 個不在本關遮住字裡的干擾字（從 `'春夏秋冬日月山水風雲花草'` 依 seed 取），依 seed 洗牌。同 seed 結果固定。
  - recite script：`{"lines": [8 句], "rounds": recite_plan.plan(...)}`；卡片寫 `stars`（一關錯 ≤2 次得一顆星，三關最多 3 顆）。每個空格 `<span class="blank" data-i="<全詩索引>">`、每個字塊 `<button class="tile" data-ch="<字>">`。點字塊：填進第一個空格；對了就固定，錯了搖一下並記錯一次。一關填滿 → 下一關；三關完 → 顯示星星與「好」→ `L.done()`。

- [ ] **Step 1：寫失敗的靜態測試（`tests/check_static.py`）**

```python
@test
def recite_plan_rules():
    import recite_plan, vocab
    r = recite_plan.plan(vocab.LINES)
    allc = ''.join(vocab.LINES)
    assert [len(x['hide']) for x in r] == [14, 27, 40], [len(x['hide']) for x in r]
    for x in r:
        hidden = {allc[i] for i in x['hide']}
        extra = [t for t in x['tiles'] if t not in hidden]
        assert len(extra) == 3, extra
        assert sorted(t for t in x['tiles'] if t in hidden) == sorted(allc[i] for i in x['hide'])
    assert recite_plan.plan(vocab.LINES) == r, '同 seed 要固定'
```

- [ ] **Step 2：跑確認失敗**

Run: `python3 tests/check_static.py`
Expected: `recite_plan_rules` FAIL（`No module named 'recite_plan'`）

- [ ] **Step 3：寫 `src/recite_plan.py`**

```python
"""背誦三關：遮哪些字、給哪些字塊。用固定 seed，每次建置結果一樣。"""
import math, random
DECOYS = '春夏秋冬日月山水風雲花草'


def plan(lines, seed=7):
    allc = ''.join(lines)
    rng = random.Random(seed)
    order = list(range(len(allc)))
    rng.shuffle(order)
    out = []
    for frac in (1 / 3, 2 / 3, 1):
        hide = sorted(order[:math.ceil(len(allc) * frac)])
        hidden = {allc[i] for i in hide}
        decoys = [c for c in DECOYS if c not in hidden]
        tiles = [allc[i] for i in hide] + rng.sample(decoys, 3)
        rng.shuffle(tiles)
        out.append({'hide': hide, 'tiles': tiles})
    return out
```

- [ ] **Step 4：跑確認通過**

Run: `python3 tests/check_static.py`
Expected: 全部通過

- [ ] **Step 5：加兩筆 SAMPLES 與失敗的卡片測試**

```python
import recite_plan, vocab
P = '/files/assets/placeholder/cg.png'
SAMPLES['order'] = {'script': {'items': [{'img': P, 'caption': f'{vocab.LINES[2*i]}，{vocab.LINES[2*i+1]}'} for i in range(4)],
                               'start': [2, 0, 3, 1]}, 'read': [], 'write': []}
SAMPLES['recite'] = {'script': {'lines': vocab.LINES, 'rounds': recite_plan.plan(vocab.LINES)}, 'read': [], 'write': ['stars']}
```

```js
cardTest('order', async (withCard, noInit) => {
  await noInit('order', '.slot');
  await withCard('order', async ui => {
    const f = await ui.frameWith('.slot');
    for (let i = 0; i < 4; i++) {           // 選擇排序：第 i 格放 data-idx=i 的那張
      const idx = await f.locator('.slot').evaluateAll(s => s.map(b => +b.dataset.idx));
      const j = idx.indexOf(i);
      if (j !== i) { await f.locator('.slot').nth(i).click(); await f.locator('.slot').nth(j).click(); }
    }
    await f.locator('#okBtn').click();
    await ui.waitText(/RESULT/);
    assert(true, '四張圖排好可以往下');
  });
});

cardTest('recite', async (withCard, noInit) => {
  await noInit('recite', '.tile');
  await withCard('recite', async ui => {
    const f = await ui.frameWith('.tile');
    let wrongOnce = false;
    while (await f.locator('.blank:not(.filled)').count()) {
      const need = await f.locator('.blank:not(.filled)').first().getAttribute('data-ch');
      if (!wrongOnce) { await f.locator(`.tile:not([data-ch="${need}"])`).first().click(); wrongOnce = true; }
      await f.locator(`.tile[data-ch="${need}"]:not(.used)`).first().click();
      await new Promise(r => setTimeout(r, 120));
    }
    await f.locator('#okBtn').click();
    const t = await ui.waitText(/RESULT/);
    assert(/stars=3/.test(t), '三關錯 ≤2 次 → 3 顆星：' + t.match(/RESULT.*/)[0]);
  }, { mobile: true });
});
```

（`.blank` 加 `data-ch` 供測試讀正解；畫面上不顯示。）

Run: `node tests/cards.mjs order && node tests/cards.mjs recite`
Expected: FAIL（HTML 不存在）

- [ ] **Step 6：寫 `src/plugin/order.html`**

```html
<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;height:100%;overflow:hidden;background:#fbf3e4;font-family:"Noto Sans TC",system-ui,sans-serif;color:#2b2b2b}
#wrap{position:absolute;inset:3vh 3vw;display:flex;flex-direction:column;align-items:center;gap:2vh}
#tip{font-size:min(5vw,3vh)}
#grid{display:grid;grid-template-columns:1fr 1fr;gap:3vw;width:100%;max-width:760px;flex:1;min-height:0}
.slot{position:relative;border:4px solid #e2d6bd;border-radius:14px;background:#fff;padding:0;overflow:hidden;cursor:pointer;min-height:44px;display:flex;flex-direction:column}
.slot img{width:100%;flex:1;min-height:0;object-fit:cover}
.slot span{font-family:"LXGW WenKai TC","BiauKai",serif;font-size:min(4vw,2.4vh);padding:4px}
.slot b{position:absolute;left:6px;top:6px;background:#2f6b4f;color:#fff;border-radius:50%;width:28px;height:28px;line-height:28px;font-size:16px}
.slot.picked{border-color:#f2b33d}
.slot.good{border-color:#2f6b4f}
#okBtn{visibility:hidden;min-width:120px;min-height:48px;border:0;border-radius:24px;background:#2f6b4f;color:#fff;font:600 min(5vw,3vh) inherit}
</style></head>
<body>
<div id="wrap"><div id="tip">點兩張圖交換位置，排成詩的順序</div><div id="grid"></div><button id="okBtn">好</button></div>
<script src="common.js"></script>
<script>
var S, pos = [], picked = -1;
function draw() {
  var g = document.getElementById('grid'); g.innerHTML = '';
  pos.forEach(function (k, i) {
    var b = document.createElement('button'); b.className = 'slot' + (k === i ? ' good' : '') + (picked === i ? ' picked' : '');
    b.dataset.idx = k;
    b.innerHTML = '<b></b><img alt=""><span></span>';
    b.querySelector('b').textContent = i + 1; b.querySelector('img').src = S.items[k].img; b.querySelector('span').textContent = S.items[k].caption;
    b.onclick = function () {
      if (picked < 0) { picked = i; }
      else { var t = pos[picked]; pos[picked] = pos[i]; pos[i] = t; picked = -1; }
      draw();
    };
    g.appendChild(b);
  });
  var solved = pos.every(function (k, i) { return k === i; });
  document.getElementById('tip').textContent = solved ? '排好了！' : '點兩張圖交換位置，排成詩的順序';
  document.getElementById('okBtn').style.visibility = solved ? 'visible' : 'hidden';
}
L.onInit(function (s) { S = s; pos = (S.start || [0, 1, 2, 3]).slice(); document.getElementById('okBtn').onclick = function () { L.done(); }; draw(); });
</script>
</body></html>
```

- [ ] **Step 7：寫 `src/plugin/recite.html`**

```html
<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;height:100%;overflow:hidden;background:#fbf3e4;font-family:"Noto Sans TC",system-ui,sans-serif;color:#2b2b2b}
#wrap{position:absolute;inset:3vh 3vw;display:flex;flex-direction:column;align-items:center;gap:2vh}
#round{font-size:min(5vw,3vh);color:#6b6257}
#poem{display:grid;grid-template-columns:1fr 1fr;gap:1vh 6vw;font-family:"LXGW WenKai TC","BiauKai","DFKai-SB",serif;font-size:min(7vw,5vh)}
.blank{display:inline-block;width:1.1em;height:1.1em;border-bottom:3px solid #d9a441;vertical-align:bottom}
.blank.filled{border-color:transparent}
#tiles{display:flex;flex-wrap:wrap;justify-content:center;gap:2vw;max-width:760px}
.tile{min-width:48px;min-height:48px;font-family:"LXGW WenKai TC","BiauKai",serif;font-size:min(7vw,4.4vh);border:2px solid #e2d6bd;border-radius:12px;background:#fff;cursor:pointer}
.tile.used{visibility:hidden}
.tile.wrong{border-color:#c8553d;animation:shake .4s}
@keyframes shake{25%{translate:-6px}75%{translate:6px}}
#end{display:none;flex-direction:column;align-items:center;gap:2vh;font-size:min(6vw,4vh)}
#okBtn{min-width:120px;min-height:48px;border:0;border-radius:24px;background:#2f6b4f;color:#fff;font:600 min(5vw,3vh) inherit}
</style></head>
<body>
<div id="wrap"><div id="round"></div><div id="poem"></div><div id="tiles"></div>
<div id="end"><div id="starsTxt"></div><button id="okBtn">好</button></div></div>
<script src="common.js"></script>
<script>
var S, r = 0, miss = 0, stars = 0, allc = '';
function round() {
  var R = S.rounds[r]; miss = 0;
  document.getElementById('round').textContent = '第 ' + (r + 1) + ' 關，共 3 關';
  var poem = document.getElementById('poem'); poem.innerHTML = '';
  var k = 0;
  S.lines.forEach(function (line) {
    var d = document.createElement('div');
    line.split('').forEach(function (c) {
      var i = k++;
      if (R.hide.indexOf(i) >= 0) { var s = document.createElement('span'); s.className = 'blank'; s.dataset.i = i; s.dataset.ch = c; d.appendChild(s); }
      else d.appendChild(document.createTextNode(c));
    });
    poem.appendChild(d);
  });
  var tiles = document.getElementById('tiles'); tiles.innerHTML = '';
  R.tiles.forEach(function (c) {
    var b = document.createElement('button'); b.className = 'tile'; b.dataset.ch = c; b.textContent = c;
    b.onclick = function () { pick(b); }; tiles.appendChild(b);
  });
}
function pick(b) {
  var blank = document.querySelector('.blank:not(.filled)'); if (!blank) return;
  if (b.dataset.ch === blank.dataset.ch) {
    blank.textContent = b.dataset.ch; blank.classList.add('filled'); b.classList.add('used');
    if (!document.querySelector('.blank:not(.filled)')) {
      if (miss <= 2) stars += 1;
      r += 1;
      if (r < S.rounds.length) setTimeout(round, 700); else setTimeout(finish, 700);
    }
  } else {
    miss += 1; b.classList.remove('wrong'); void b.offsetWidth; b.classList.add('wrong');
  }
}
function finish() {
  L.set('stars', stars);
  document.getElementById('poem').style.display = 'none'; document.getElementById('tiles').style.display = 'none';
  document.getElementById('round').textContent = '全部背完了！';
  document.getElementById('starsTxt').textContent = '得到 ' + stars + ' 顆星';
  document.getElementById('end').style.display = 'flex';
}
L.onInit(function (s) { S = s; document.getElementById('okBtn').onclick = function () { L.done(); }; round(); });
</script>
</body></html>
```

- [ ] **Step 8：跑測試確認通過**

Run: `node tests/cards.mjs order && node tests/cards.mjs recite`
Expected: 全部 `ok`

- [ ] **Step 9：規格同步**

`docs/specs/2026-10-05-design.md` 第 4 節表格「四張圖排順序」那列的「拖成正確順序」改成「點兩張交換位置，排成正確順序（手機上拖曳不好操作）」。

- [ ] **Step 10：Commit**

```bash
git add src/plugin/order.html src/plugin/recite.html src/recite_plan.py src/plugin.py tests docs/specs/2026-10-05-design.md
git commit -m "feat: 四張圖排順序與背誦闖關"
```

---

### Task 7：建置 build.py、佔位圖、全路徑試玩

**Files:**
- Create: `src/art.py`、`src/placeholders.py`、`src/build.py`、`tests/play_all.mjs`、`poems/guo-guren-zhuang/script.md`（測試用短劇本，Task 8 換成正式版）
- Modify: `tests/check_static.py`

**Interfaces:**
- Consumes: `script.load`、`vocab.load`、`vocab.LINES`、`plugin.card_node`、`cards.*`、`variables.project_variables`、`recite_plan.plan`
- Produces:
  - `art.paths() -> dict[key -> url]`；鍵：背景 `bg-<name>`、CG `cg-1`～`cg-6`（`cg-1`～`cg-4` 是四張圖）、生字 `v-<id>`、生字音 `a-<id>`、跟念音 `f-<pair>`。正式檔在 `poems/guo-guren-zhuang/art/` 或 `audio/`，不在就退回 `assets/placeholder/`（音檔退回空字串）。網址形式 `/files/assets/<相對路徑>`；`build.mirror_assets` 把 `poems/guo-guren-zhuang/art`、`audio` 與 `assets/` 鏡像進 `dist/assets/`。
  - `build.build() -> dict`、`build.load_skeleton()`、`build.mirror_assets(dst)`、`build.PROJECT_ID`
  - 節點 id 規則：場景對話卡 `<scene>-<k>`、生字卡 `v-<id>`、解釋卡 `x-<id>`、跟念 `f-<pair>`、複習跳板 `h-<n>`、複習卡 `r-<id>`、排圖 `order`、背誦 `recite`、結算 `summary`。

- [ ] **Step 1：寫測試用短劇本 `poems/guo-guren-zhuang/script.md`**

```
# s0 開場 | bg=study
小樂：這本書在發光！
# s1 故人具雞黍 | bg=gate
故人：請到我家來吃飯。
@生字 雞黍
@生字 具
@跟念 0
# s5 收尾 | bg=study
@排圖
@複習
@背誦
@結算
# explain
## 雞黍
故人：黍是黃黃的小米。
```

- [ ] **Step 2：寫失敗的靜態測試**

```python
def _built():
    import build
    return build.build()

@test
def build_flow():
    p = _built()
    b = p['boards'][0]
    ids = {n['id'] for n in b['nodes']}
    for need in ('v-jishu', 'x-jishu', 'f-0', 'order', 'recite', 'summary', 'r-jishu'):
        assert need in ids, need
    out = lambda a: [e for e in b['edges'] if e['source'] == a]
    vj = out('v-jishu')
    assert any(e.get('data', {}).get('condition', {}).get('variable') == 'last_ok' and e['target'] == 'x-jishu' for e in vj), vj
    assert any('data' not in e for e in vj), '生字卡要有一條無條件的預設出口'
    assert [e['target'] for e in out('x-jishu')] == ['v-jishu'], '解釋完回到同一張生字卡'
    starts = [n for n in b['nodes'] if n['data'].get('start')]
    assert len(starts) == 1

@test
def every_node_reaches_end():
    p = _built(); b = p['boards'][0]
    nxt = {}
    for e in b['edges']: nxt.setdefault(e['source'], []).append(e['target'])
    for n in b['nodes']:
        seen, todo = set(), [n['id']]
        while todo:
            x = todo.pop()
            if x in seen: continue
            seen.add(x); todo += nxt.get(x, [])
        assert 'summary' in seen, f"{n['id']} 走不到結算"

@test
def gate_matches_script():
    import variables
    for n in _built()['boards'][0]['nodes']:
        d = n['data']
        if d.get('type') != 'plugin': continue
        s = json.loads(d['pluginValues']['script'])
        if d['pluginCardId'] == 'vocab' and s.get('quiz'):
            assert set(d['pluginWriteVars']) == {s['gotVar'], 'learned', 'last_ok'}, n['id']
            assert set(d['pluginReadVars']) == {s['gotVar'], 'learned'}, n['id']
        for v in d['pluginReadVars'] + d['pluginWriteVars']: assert v in variables.VARS, (n['id'], v)

@test
def vocab_cards_have_media():
    for n in _built()['boards'][0]['nodes']:
        d = n['data']
        if d.get('pluginCardId') == 'vocab':
            s = json.loads(d['pluginValues']['script'])
            assert s['img'], n['id']
            for o in s.get('options', []): assert o['img'], n['id']
```

- [ ] **Step 3：跑確認失敗**

Run: `python3 tests/check_static.py`
Expected: 四個新測試 FAIL（`No module named 'build'`）

- [ ] **Step 4：寫 `src/placeholders.py`（產佔位圖，結果進版控）**

```python
"""產 assets/placeholder/ 的純色佔位圖（標上鍵名），正式美術到位前讓建置跑得動。python3 src/placeholders.py"""
import pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets/placeholder'
SPECS = {'bg.png': ('1920x1080', '#cfe8f3'), 'cg.png': ('1920x1080', '#f2c14e'), 'vocab.png': ('512x512', '#c9e4b4')}

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (size, color) in SPECS.items():
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', f'color=c={color}:s={size}',
                        '-frames:v', '1', str(OUT / name)], check=True)
    print('wrote', OUT)
```

Run: `python3 src/placeholders.py`

- [ ] **Step 5：寫 `src/art.py`**

```python
"""美術與音檔路徑：正式檔在 poems/<詩>/art|audio，不在就退回佔位圖（音檔退回空字串）。"""
import pathlib
import vocab
ROOT = pathlib.Path(__file__).resolve().parent.parent
POEM = ROOT / 'poems/guo-guren-zhuang'
BGS = ('study', 'gate', 'road', 'room', 'fence')


def _pick(rel, fallback):
    for ext in ('.webp', '.png', '.jpg', '.mp3'):
        f = POEM / (rel + ext)
        if f.exists(): return '/files/assets/' + str(f.relative_to(POEM))
    return fallback


def paths():
    a = {f'bg-{b}': _pick(f'art/bg/{b}', '/files/assets/placeholder/bg.png') for b in BGS}
    a.update({f'cg-{i}': _pick(f'art/cg/{i}', '/files/assets/placeholder/cg.png') for i in range(1, 7)})
    for e in vocab.load():
        a[f"v-{e['id']}"] = _pick(f"art/vocab/{e['id']}", '/files/assets/placeholder/vocab.png')
        a[f"a-{e['id']}"] = _pick(f"audio/vocab/{e['id']}", '')
    a.update({f'f-{i}': _pick(f'audio/follow/{i}', '') for i in range(4)})
    return a
```

- [ ] **Step 6：寫 `src/build.py`**

```python
"""組出 dist/project.json：骨架＋劇本對話卡＋tangshi-kit 插件卡＋有條件連線。"""
import json, os, pathlib, random, shutil
import art, cards, plugin, recite_plan, script, variables, vocab
ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT_ID = '<Task 1 Step 1 拿到的 project id>'   # 執行 Task 1 時填入實際值


def load_skeleton():
    return json.loads((ROOT / 'skeleton/project.json').read_text())


def vocab_script(e, a, by_word, review=False):
    s = {'word': e['word'], 'zhuyin': e['zhuyin'], 'meaning': e['meaning'], 'img': a[f"v-{e['id']}"],
         'audio': a[f"a-{e['id']}"], 'quiz': e['core'], 'retry': not review, 'review': review,
         'gotVar': f"got_{e['id']}", 'ask': f"「{e['word']}」是什麼意思？"}
    if e['core']:
        rng = random.Random(e['id'])                   # 干擾選項：其他生字的圖與解釋，每次建置一樣
        others = rng.sample([o for o in by_word.values() if o['id'] != e['id']], 2)
        opts = [{'img': a[f"v-{e['id']}"], 'label': e['meaning'], 'ok': True}] + \
               [{'img': a[f"v-{o['id']}"], 'label': o['meaning'], 'ok': False} for o in others]
        rng.shuffle(opts)
        s['options'] = opts
    return s


def vocab_node(e, a, by_word, node_id, review=False):
    s = vocab_script(e, a, by_word, review)
    if e['core']:
        g = f"got_{e['id']}"
        return plugin.card_node('vocab', node_id, s, read=[g, 'learned'], write=[g, 'learned', 'last_ok'])
    return plugin.card_node('vocab', node_id, s, read=[], write=[])


def build():
    p = load_skeleton()
    board = p['boards'][0]
    board['nodes'], board['edges'] = [], []
    p['nodes'], p['edges'] = board['nodes'], board['edges']
    p['variables'] = variables.project_variables()
    p['settings']['plugins'][plugin.PLUGIN_ID] = plugin.settings_entry()
    p['settings'].update({'stageFit': 'auto', 'keepActorsInFrame': False, 'cgGalleryEnabled': False})
    a = art.paths()
    sc = script.load()
    by_word = {e['word']: e for e in vocab.load()}
    N, L = board['nodes'].append, (lambda x, y, **k: cards.link(board, x, y, **k))
    prev, first = None, True
    core_order = []

    def chain(node_id):
        nonlocal prev
        if prev: L(prev, node_id)
        prev = node_id

    for scene in sc['scenes']:
        bg = a.get(f"bg-{scene['bg']}", '')
        buf, k = [], 0

        def flush():
            nonlocal buf, k, first
            if not buf: return
            nid = f"{scene['id']}-{k}"; k += 1
            N(cards.dialogue(nid, scene['title'], [(i['speaker'] if i['speaker'] != '旁白' else '', i['text']) for i in buf],
                             bg=bg, start=first))
            first = False; buf = []
            chain(nid)

        for it in scene['items']:
            if it['kind'] == 'line': buf.append(it); continue
            flush()
            if it['kind'] == 'vocab':
                e = by_word[it['word']]
                vid = f"v-{e['id']}"
                N(vocab_node(e, a, by_word, vid))
                chain(vid)
                if e['core']:
                    core_order.append(e)
                    xid = f"x-{e['id']}"
                    N(cards.dialogue(xid, f"再說一次：{e['word']}", sc['explain'][e['word']], bg=bg))
                    L(vid, xid, cond=('last_ok', 'eq', False))
                    L(xid, vid)
            elif it['kind'] == 'follow':
                i = it['pair']
                fid = f'f-{i}'
                N(plugin.card_node('follow', fid, {'lines': vocab.LINES[2 * i:2 * i + 2], 'audio': a[f'f-{i}'], 'marks': []}, [], []))
                chain(fid)
            elif it['kind'] == 'order':
                items = [{'img': a[f'cg-{i + 1}'], 'caption': f'{vocab.LINES[2 * i]}，{vocab.LINES[2 * i + 1]}'} for i in range(4)]
                N(plugin.card_node('order', 'order', {'items': items, 'start': [2, 0, 3, 1]}, [], []))
                chain('order')
            elif it['kind'] == 'review':
                # 跳板 h-n：got==0 → 複習卡 r-id → 下一個跳板；否則直接下一個跳板
                for n, e in enumerate(core_order):
                    hid, rid = f'h-{n}', f"r-{e['id']}"
                    N(cards.setvar(hid, f"複習：{e['word']}", [{'variable': 'hop', 'op': 'set', 'value': n}]))
                    chain(hid)
                    N(vocab_node(e, a, by_word, rid, review=True))
                    L(hid, rid, cond=(f"got_{e['id']}", 'eq', 0))
                    nxt = f'h-{n + 1}' if n + 1 < len(core_order) else 'h-end'
                    L(rid, nxt)
                N(cards.setvar('h-end', '複習結束', [{'variable': 'hop', 'op': 'set', 'value': len(core_order)}]))
                chain('h-end')
            elif it['kind'] == 'recite':
                N(plugin.card_node('recite', 'recite', {'lines': vocab.LINES, 'rounds': recite_plan.plan(vocab.LINES)}, [], ['stars']))
                chain('recite')
            elif it['kind'] == 'summary':
                core_n = len(core_order)   # 劇本裡實際出現的核心字數；正式劇本會是 12
                N(cards.dialogue('summary', '結算', [f'這一趟，你學會了 {{{{learned}}}} 個字（一共 {core_n} 個）。',
                                                     '背誦拿到 {{stars}} 顆星。'], bg=bg))
                chain('summary')
        flush()
    return p


def main():
    p = build()
    out = ROOT / 'dist/project.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(p, ensure_ascii=False))
    mirror_assets(out.parent / 'assets')
    print('wrote', out, len(p['boards'][0]['nodes']), 'nodes')


def mirror_assets(dst):
    """serve.py 只提供 JSON 所在資料夾裡的真實檔案（符號連結會被擋），所以用硬連結鏡像。"""
    def link(src, d):
        try: os.link(src, d)
        except OSError: shutil.copy2(src, d)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(ROOT / 'assets', dst, copy_function=link)
    for sub in ('art', 'audio'):
        src = ROOT / 'poems/guo-guren-zhuang' / sub
        if src.exists(): shutil.copytree(src, dst / sub, copy_function=link)


if __name__ == '__main__':
    main()
```

注意：`chain()` 讓前一張的「無條件出口」接到下一張；生字卡同時有 `last_ok==false → x-…` 的條件邊，Larch 依「有條件先判、無條件當預設」路由（larch-vn 2026-09-06 實測）。

- [ ] **Step 7：跑靜態測試確認通過**

Run: `python3 tests/check_static.py`
Expected: 全部通過

- [ ] **Step 8：寫 `tests/play_all.mjs`（三條路徑）**

```js
// 全路徑：node tests/play_all.mjs [right|wrong|all]
import { serve, open, assert, sleep } from './lib.mjs';
import { execFileSync } from 'node:child_process';
execFileSync('python3', ['src/build.py'], { stdio: 'inherit' });
const which = process.argv[2] || 'all';

async function run(mode) {   // mode: right＝全對；wrong＝每個核心字先錯一次
  const s = await serve('dist/project.json');
  const ui = await open(s.base, { mobile: true });
  const wrongDone = new Set(); let sawExplain = 0, sawReview = 0;
  try {
    await ui.clickText('開始遊戲').catch(() => {});
    for (let step = 0; step < 600; step++) {
      const t = await ui.text();
      if (/學會了 \d+ 個字/.test(t)) break;
      if (/再說一次：/.test(t)) sawExplain++;
      const v = await ui.frameWith('button[data-ok]');
      if (v && await v.locator('button[data-ok]').first().isVisible()) {
        const word = await v.locator('#word').innerText();
        const review = await v.evaluate(() => document.body.dataset.review === '1');
        if (review) sawReview++;
        const wrong = mode === 'wrong' && !review && !wrongDone.has(word);
        if (wrong) wrongDone.add(word);
        await v.locator(`button[data-ok="${wrong ? 0 : 1}"]`).first().click();
        await sleep(900);
        if (!wrong) await v.locator('#okBtn').click().catch(() => {});
        await sleep(600); continue;
      }
      const ok = await ui.frameWith('#okBtn');
      const o = await ui.frameWith('.slot'), r = await ui.frameWith('.tile');
      if (o && await o.locator('.slot').first().isVisible()) {
        for (let i = 0; i < 4; i++) {
          const idx = await o.locator('.slot').evaluateAll(x => x.map(b => +b.dataset.idx));
          const j = idx.indexOf(i);
          if (j !== i) { await o.locator('.slot').nth(i).click(); await o.locator('.slot').nth(j).click(); }
        }
        await o.locator('#okBtn').click(); await sleep(600); continue;
      }
      if (r && await r.locator('.blank:not(.filled)').count()) {
        const need = await r.locator('.blank:not(.filled)').first().getAttribute('data-ch');
        await r.locator(`.tile[data-ch="${need}"]:not(.used)`).first().click(); await sleep(150); continue;
      }
      if (ok && await ok.locator('#okBtn').isVisible()) { await ok.locator('#okBtn').click(); await sleep(600); continue; }
      await ui.advance(); await sleep(500);
    }
    const t = await ui.waitText(/學會了 \d+ 個字/, 5000);
    const learned = +t.match(/學會了 (\d+) 個字/)[1];
    const core = +t.match(/一共 (\d+) 個/)[1];
    if (mode === 'right') assert(learned === core && sawExplain === 0 && sawReview === 0, `全對：學會 ${learned}/${core}，沒有解釋與複習`);
    if (mode === 'wrong') assert(sawExplain >= core && sawReview === core && learned === core, `全錯一次：解釋 ${sawExplain}、複習 ${sawReview}、學會 ${learned}/${core}`);
    assert(/3 顆星/.test(t), '背誦三關全過拿 3 顆星');
    assert(ui.errors.length === 0, '沒有頁面例外 ' + ui.errors.join(';'));
  } finally { await ui.close(); s.kill(); }
}
if (which === 'all' || which === 'right') await run('right');
if (which === 'all' || which === 'wrong') await run('wrong');
```

- [ ] **Step 9：跑全路徑**

Run: `node tests/play_all.mjs`
Expected: 兩條都 `ok`（測試用短劇本只有一個核心字，結算顯示「一共 1 個」）。

如果複習跳板（setVariable 卡）在播放器上停住等點擊，改成 `cards.dialogue` 不行（會多出空白對話），改用 scene 卡加 `autoAdvance:{enabled:true, mode:'delay', delayMs:0}`：`cards.setvar` 的 data 加上 `'autoAdvance': {'enabled': True, 'mode': 'delay', 'delayMs': 0}` 再跑一次。

- [ ] **Step 10：Commit**

```bash
git add src/art.py src/placeholders.py src/build.py assets/placeholder poems/guo-guren-zhuang/script.md tests
git commit -m "feat: build.py 組專案、佔位圖、全路徑試玩"
```

---

### Task 8：正式劇本（作者把關）

**Files:**
- Modify: `poems/guo-guren-zhuang/script.md`
- Modify: `tests/check_static.py`

- [ ] **Step 1：加劇本規則的靜態測試**

```python
@test
def script_covers_all_vocab():
    import script, vocab
    s = script.load()
    used = [i['word'] for sc in s['scenes'] for i in sc['items'] if i['kind'] == 'vocab']
    words = [e['word'] for e in vocab.load()]
    assert sorted(used) == sorted(words), set(words) ^ set(used)
    for e in vocab.load():
        if e['core']: assert s['explain'].get(e['word']), f"{e['word']} 沒有答錯解釋"
    follows = [i['pair'] for sc in s['scenes'] for i in sc['items'] if i['kind'] == 'follow']
    assert follows == [0, 1, 2, 3], follows

@test
def script_poem_quotes_exact():
    import script, vocab, re
    for sc in script.load()['scenes']:
        for i in sc['items']:
            if i['kind'] == 'line':
                for q in re.findall(r'「([^」]{5,})」', i['text']):
                    if any(c in q for c in '雞黍軒郭桑麻菊') and '，' in q:
                        assert q.rstrip('。') in vocab.POEM, f'詩句引錯：{q}'
```

- [ ] **Step 2：寫正式劇本**

依規格第 3 節六段寫：開場（s0）、四幕（s1～s4）、收尾（s5：`@排圖` → `@複習` → `@背誦` → `@結算` → 回到現代）。每幕：故事台詞 → 該兩句詩裡的生字（照詩句順序，23 個全用上）→ `@跟念 <幕-1>`。`# explain` 寫 12 個核心字各 2～4 句換個說法的解釋，由劇中角色講，口吻給八歲孩子聽。內容依 `考證.md`。台詞控制在全程 12～15 分鐘（約 150～200 句）。

- [ ] **Step 3：檢查**

Run: `python3 tests/check_static.py && speak-tw poems/guo-guren-zhuang/script.md && grep -c "——" poems/guo-guren-zhuang/script.md`
Expected: 全部通過；speak-tw 0 處；破折號 0

- [ ] **Step 4：作者確認**

用 `/larch-preview` 開本機播放器（`python3 src/build.py && python3 ~/larch-preview/serve.py dist/project.json`）給作者試玩，**停下來等作者回饋**；回饋在 `feedback.jsonl`，照改到作者說可以。

- [ ] **Step 5：全路徑再跑一次並 Commit**

Run: `node tests/play_all.mjs`
Expected: 兩條都 `ok`

```bash
git add poems/guo-guren-zhuang/script.md tests/check_static.py
git commit -m "feat: 〈過故人莊〉正式劇本"
```

---

### Task 9：美術

**Files:**
- Create: `canon/角色/*.png`、`poems/guo-guren-zhuang/art/{bg,cg,vocab,char}/…`、`poems/guo-guren-zhuang/art/產圖紀錄.md`
- Modify: `src/art.py`（加角色立繪鍵）、`src/build.py`（對話卡 `stage.actors`）、`src/cards.py`（`dialogue` 加 `actors` 參數）

規矩：先讀 `cast-lock` skill；工具用 `codex-imagegen` skill（本機 codex）或 .11 codex-image；去背用 `cutout` skill；產圖一次一張、從頭產不疊修；每張 CG 的提示詞列在場角色並附定錨圖；出圖逐項對 `考證.md` 與 `canon/系列角色.md` 驗；轉小再 commit（webp，背景與 CG 寬 1920，生字圖 512）。

- [ ] **Step 1：主角定錨**：阿禾、小樂各一張全身正面定錨（白底），依 `canon/系列角色.md`。**給作者看，作者選定才往下。**
- [ ] **Step 2：唐朝角色定錨**：孟浩然、故人各一張。給作者看。
- [ ] **Step 3：立繪與表情**：四人各 3～4 個表情（平常、開心、驚訝、想事情），去背成透明 PNG，跑 `cutout` 的驗收。存 `art/char/<角色>-<表情>.webp`。
- [ ] **Step 4：背景 5 張**：study、gate、road、room、fence，存 `art/bg/`。
- [ ] **Step 5：CG 6 張**：`cg/1`～`cg/4` 對應四聯（四張圖記憶法，各一張能一眼認出是哪兩句），`cg/5` 開場掉進詩卷、`cg/6` 回到現代。帶在場角色定錨。給作者看 1～4。
- [ ] **Step 6：生字圖 23 張**：一字一張、512×512、同一畫風；黍畫黃色小米粒，不能是稻米。
- [ ] **Step 7：接上立繪**：`cards.dialogue` 加 `actors=None` 參數寫進 `stage.actors`；`build.py` 依台詞講者帶入對應立繪（表情取 `〔表情〕` 標記，劇本格式 `講者〔表情〕：台詞`，`script.parse` 一併支援並加測試 `('孟浩然〔開心〕：好。' → speaker='孟浩然', expr='開心')`）。
- [ ] **Step 8：驗收**：`python3 tests/check_static.py && node tests/play_all.mjs`，再用 `/larch-preview` 給作者看整體。
- [ ] **Step 9：Commit**（只 add 這次的圖與程式）

---

### Task 10：配音與生字音

**Files:**
- Create: `src/vocab_audio.py`、`poems/guo-guren-zhuang/audio/vocab/*.mp3`、`poems/guo-guren-zhuang/audio/follow/*.mp3`、`poems/guo-guren-zhuang/audio/讀音驗收.md`

- [ ] **Step 1：寫 `src/vocab_audio.py`**

```python
"""生字與跟念音檔：送 larch-tts-bridge（.11:8072），文字用 vocab.json 的 tts 替身字。已存在的檔跳過。
    python3 src/vocab_audio.py
"""
import json, os, pathlib, urllib.request
import vocab
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'poems/guo-guren-zhuang/audio'
URL = os.environ.get('TTS_URL', 'http://192.168.11.11:8072/tts')
VOICE = os.environ.get('TTS_VOICE', 'Chinese (Mandarin)_Wise_Women')
SUBS = {'斜': '霞', '郭': '鍋', '還': '孩'}   # 跟念整句用的替身


def tts(text, dst):
    if dst.exists(): return
    dst.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps({'text': text, 'voice': VOICE, 'format': 'mp3'}).encode()
    r = urllib.request.Request(URL, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(r, timeout=300) as resp: dst.write_bytes(resp.read())
    print('wrote', dst, flush=True)


if __name__ == '__main__':
    for e in vocab.load(): tts(e['tts'] + '。', OUT / 'vocab' / f"{e['id']}.mp3")
    for i in range(4):
        line = '，'.join(vocab.LINES[2 * i:2 * i + 2]) + '。'
        tts(''.join(SUBS.get(c, c) for c in line), OUT / 'follow' / f'{i}.mp3')
```

（bridge 是一次一句、全域鎖，所以這支依序跑，不並行。）

- [ ] **Step 2：跑並驗讀音**：`python3 src/vocab_audio.py`；用 `/llmshare` 或本機 whisper 把 27 個檔轉成拼音逐字比對，結果寫進 `讀音驗收.md`；斜、郭、還、場四個檔**請作者親耳聽**。不對的刪檔改替身字重跑。
- [ ] **Step 3：劇情配音**：讀 `larch-vn` skill 的配音章節。專案設 `project.languages = [{"code":"zh-Hant","label":"繁體中文","voiceMode":"shared"}]`；`POST /voice/generate` 一句一次、並行 3、能續跑（已有 `voiceUrl` 跳過）。之後重推版子要把伺服器上的 `voiceUrl` 帶回來（`push.py` 加：PUT 前依 `dialogueLines[].id` 從線上複製 `voiceUrl`，文字有變的那句不帶）。四個角色與旁白的聲線先各配三句給作者挑。
- [ ] **Step 4：跟念 marks**：`follow` 卡的 `marks` 從音檔量：用 ffmpeg `silencedetect` 抓逗號停頓，前後兩句各平均分五字；寫進 `build.py`（`marks` 由 `art.py` 旁的 `audio/follow/<i>.json` 提供，沒有就空陣列）。
- [ ] **Step 5：驗收並 Commit**：`node tests/play_all.mjs`；`git add src/vocab_audio.py poems/guo-guren-zhuang/audio src/push.py src/build.py`

---

### Task 11：推上 Larch、標題畫面、README

**Files:**
- Modify: `src/build.py`（標題、封面、簡介）、`README.md`

- [ ] **Step 1：標題與封面**：`p['name'] = '唐詩小旅行：過故人莊'`；`settings.titleCoverImage = a['cg-5']`；`projectThumbnail` 用另一張帶標題的圖；簡介（`p['description']`）只講內容與玩法，寫完跑 `speak-tw`。
- [ ] **Step 2：推送**：`python3 src/push.py "第一版"`；確認輸出「讀回比對通過」。
- [ ] **Step 3：插件草稿**：用 MCP `larch_save_plugin_draft` 送 `plugin.manifest()`（上架只能網頁後台按，告訴作者）。
- [ ] **Step 4：線上冒煙**：用 `larch_share_link` 拿試玩連結，Playwright 跑 `play_all.mjs` 的 `right` 模式對線上網址一次（`serve` 換成直接 `open(<網址>)`）。
- [ ] **Step 5：README**：補上 Larch 試玩連結、指令表（build、preview、check_static、cards、play_all、vocab_audio、push）、目錄說明；跑 `speak-tw README.md`。
- [ ] **Step 6：Commit、push**

```bash
git add src/build.py README.md
git commit -m "feat: 標題畫面、推上 Larch、README"
git push
```

- [ ] **Step 7：交給作者**：回報試玩連結，**發佈由作者在網頁按**。
