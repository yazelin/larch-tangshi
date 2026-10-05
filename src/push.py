"""推到 Larch：快照 → 素材網址換成 jsDelivr（釘 commit）→ 整包 PUT（包在 {"project": …}）→ 讀回比對 → 預熱 jsDelivr。
素材不再上傳到 Larch：Larch 的媒體在 pub-*.r2.dev，那是 R2 的開發網址，不快取又限流（實測每次 0.6～1.7 秒），
jsDelivr 熱快取 0.1～0.2 秒。素材要先 commit 並推上 GitHub，jsDelivr 才抓得到。

    python3 src/push.py "這次改了什麼"
"""
import json, os, re, sys, time, base64, pathlib, urllib.request, urllib.error, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
import build

ROOT = build.ROOT
KEY = open(os.path.expanduser(os.environ.get('LARCH_KEY_FILE', '~/.config/larch/key'))).read().strip()
BASE = f'https://larch.ink/api/agent/projects/{build.PROJECT_ID}'
MIME = {'.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.mp3': 'audio/mpeg'}


_open, _sleep = urllib.request.urlopen, time.sleep   # 測試會換掉


class HttpFail(SystemExit):
    """請求失敗；status 是 HTTP 狀態碼，網路錯誤或逾時是 None。"""
    def __init__(self, msg, status=None):
        super().__init__(msg); self.status = status


def req(method, path='', body=None, etag=None, tries=6):
    """429、5xx、網路錯誤都退避重試；其他 HTTP 錯誤直接結束。"""
    h = {'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'}
    if etag: h['If-Match'] = etag
    last = None
    for t in range(tries):
        try:
            r = urllib.request.Request(BASE + path, method=method, headers=h, data=json.dumps(body).encode() if body is not None else None)
            with _open(r, timeout=180) as resp:
                return resp.headers.get('ETag'), json.loads(resp.read() or b'{}')
        except urllib.error.HTTPError as e:
            last = f'{e.code} {e.read()[:300]}'
            if e.code != 429 and e.code < 500 or tries == 1: raise HttpFail(f'{method} {path} → {last}', e.code)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = repr(e)
            if tries == 1: raise HttpFail(f'{method} {path} → {last}')
        print(f'{method} {path} 失敗（{last}），{10 * (t + 1)} 秒後重試', flush=True)
        _sleep(10 * (t + 1))
    raise HttpFail(f'{method} {path} 重試 {tries} 次仍失敗：{last}')


GENERATED_PLUGINS = ('tangshi-kit',)
GENERATED_KEYS = ('titleCoverImage', 'projectThumbnail', 'stageFit', 'keepActorsInFrame', 'cgGalleryEnabled', 'aiDirectorAllowImprovisation')


def merge_settings(online, built):
    """以線上設定為底，只覆寫產生器負責的鍵：自製插件、封面、縮圖、舞台設定。作者在網頁改的其他設定保留。"""
    m = json.loads(json.dumps(online or {}))
    plugins = m.setdefault('plugins', {})
    for k in GENERATED_PLUGINS:
        plugins[k] = built['plugins'][k]
    for k in GENERATED_KEYS:
        if k in built: m[k] = built[k]
    return m


REPO = 'yazelin/larch-tangshi'
POEM_DIR = 'poems/guo-guren-zhuang'


def _git(*args):
    import subprocess
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def repo_path(rel):
    """/files/assets/<rel> 對應的 repo 路徑：placeholder/ 在 assets/，art/、audio/ 在詩的資料夾。"""
    return f'assets/{rel}' if rel.startswith('placeholder/') else f'{POEM_DIR}/{rel}'


def cdn_url(rel, sha):
    return f'https://cdn.jsdelivr.net/gh/{REPO}@{sha}/{repo_path(rel)}'


def to_cdn(text):
    """把 /files/assets/… 換成 jsDelivr 網址，每個檔釘在它自己最後一次改動的 commit：
    沒改的檔網址不變，jsDelivr 快取一直是熱的（釘 HEAD 的話每推一次 201 個檔全部要冷抓）。
    素材沒 commit、或 HEAD 還沒推上 GitHub 就中止。"""
    sha = _git('rev-parse', 'HEAD').strip()
    dirty = [l for l in _git('status', '--porcelain', '--', 'assets', POEM_DIR).splitlines() if l.strip()]
    if dirty: raise SystemExit(f'素材有沒 commit 的變更，jsDelivr 抓不到：{dirty[:5]}')
    if not _git('branch', '-r', '--contains', sha).strip():
        raise SystemExit(f'{sha[:7]} 還沒推上 GitHub，jsDelivr 抓不到；先 git push')
    last = {}
    def pin(m):
        rel = m.group(1)
        if rel not in last: last[rel] = _git('log', '-1', '--format=%H', '--', repo_path(rel)).strip()
        if not last[rel]: raise SystemExit(f'{repo_path(rel)} 沒有 commit 紀錄')
        return cdn_url(rel, last[rel])
    return re.sub(r'/files/assets/([\w./-]+\.(?:png|webp|jpg|mp3))', pin, text)


def prewarm(text):
    """每個 jsDelivr 網址先抓一次，第一位玩家才不會碰到冷快取（冷 2 秒多、熱 0.1～0.2 秒）。"""
    from concurrent.futures import ThreadPoolExecutor
    urls = sorted(set(re.findall(r'https://cdn\.jsdelivr\.net/gh/[^"\\]+', text)))
    def get(u):
        q = urllib.parse.quote(u, safe=':/@')
        for t in range(2):   # 冷快取第一次可能要 40 秒以上
            try:
                with _open(urllib.request.Request(q, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120) as r: return r.status
            except urllib.error.HTTPError as e: code = e.code
            except Exception: code = 0
        return code
    with ThreadPoolExecutor(8) as ex: codes = list(ex.map(get, urls))
    bad = [u for u, c in zip(urls, codes) if c != 200]
    print(f'預熱 jsDelivr：{len(urls) - len(bad)}/{len(urls)} 個檔回 200', flush=True)
    if bad: raise SystemExit(f'專案已經推上去了，但這些檔 jsDelivr 抓不到（玩家會看不到）：{bad[:5]}')


def content_key(board):
    """比對用的內容指紋：卡片 id、台詞、插件內容、背景、連線。只比數量會把「沒寫進去」當成功。"""
    def node(n):
        d = n['data']
        return (n['id'], d.get('type'), d.get('background'), [l.get('text') for l in d.get('dialogueLines') or []],
                (d.get('pluginValues') or {}).get('script'))
    return json.dumps([[node(n) for n in board['nodes']], sorted((e['source'], e['target']) for e in board['edges'])],
                      ensure_ascii=False, sort_keys=True)


def put_project(project, summary, etag, built_board):
    """整包 PUT 一次，不自動重送。409/412 是網頁上有人改過（If-Match 擋下來），其他 4xx 是被拒；
    只有逾時與 5xx 才讀回比對內容，判斷其實有沒有寫進去。"""
    try:
        req('PUT', '', {'project': project, 'summary': summary}, etag, tries=1)
        return
    except HttpFail as e:
        if e.status in (409, 412):
            raise SystemExit(f'PUT 被擋下（{e.status}）：抓快照之後網頁上有人改過專案。先看網頁上改了什麼，再重新推。')
        if e.status is not None and e.status < 500 and e.status != 429:
            raise SystemExit(f'PUT 被拒：{e}')
        _, chk = req('GET'); chk = chk.get('project', chk)
        if content_key(chk['boards'][0]) == content_key(built_board):
            print('PUT 回應失敗，但讀回內容已經是新版：', e)
            return
        raise SystemExit(f'PUT 失敗而且線上沒有更新（{e}）。沒有自動重送，避免蓋掉別人的修改；確認後重跑。')


def main(summary):
    etag, cur = req('GET')
    online = cur.get('project', cur)
    snap = ROOT / 'snapshots' / time.strftime('%Y%m%d-%H%M%S.json')
    snap.parent.mkdir(exist_ok=True)
    snap.write_text(json.dumps(cur, ensure_ascii=False))
    print('快照', snap)

    build.main()
    built = build.build()
    text = json.dumps(built, ensure_ascii=False)
    text = to_cdn(text)
    left = re.findall(r'/files/assets/[^"\\]+', text)
    if left: raise SystemExit(f'還有沒換掉的本機路徑：{left[:5]}')
    built = json.loads(text)

    etag, cur = req('GET')  # 抓最新的 etag
    online = cur.get('project', cur)
    project = dict(online)
    if len(online.get('boards', [])) > len(built['boards']):
        raise SystemExit(f"線上有 {len(online['boards'])} 塊白板、本機只有 {len(built['boards'])} 塊；推送會蓋掉多的那塊，先確認")
    for k in ('boards', 'nodes', 'edges', 'variables', 'activeBoardId', 'name', 'description', 'languages'):
        project[k] = built[k]
    project['settings'] = merge_settings(online.get('settings'), built['settings'])
    put_project(project, summary, etag, built['boards'][0])

    _, back = req('GET')
    back = back.get('project', back)
    b0, w0 = back['boards'][0], built['boards'][0]
    def check(ok, msg):
        if not ok: raise SystemExit('讀回比對失敗：' + msg)
    check(len(b0['nodes']) == len(w0['nodes']), f"節點數 {len(b0['nodes'])} ≠ {len(w0['nodes'])}")
    check(content_key(b0) == content_key(w0), '卡片內容（台詞、插件、背景、連線）跟本機不一樣')
    check(len(b0['edges']) == len(w0['edges']), f"連線數 {len(b0['edges'])} ≠ {len(w0['edges'])}")
    check('tangshi-kit' in back['settings']['plugins'], '插件設定不見了')
    check(len(back['variables']) == len(built['variables']), '變數數量不符')
    prewarm(text)
    print('推送完成，讀回比對通過：', len(b0['nodes']), '張卡、', len(b0['edges']), '條線')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '更新')
