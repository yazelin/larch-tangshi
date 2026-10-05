"""推到 Larch：快照 → 上傳用到的圖 → 換網址 → 整包 PUT（包在 {"project": …}）→ 讀回比對。

    python3 src/push.py "這次改了什麼"
"""
import json, os, re, sys, time, base64, pathlib, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(__file__))
import build

ROOT = build.ROOT
KEY = open(os.path.expanduser(os.environ.get('LARCH_KEY_FILE', '~/.config/larch/key'))).read().strip()
BASE = f'https://larch.ink/api/agent/projects/{build.PROJECT_ID}'
UPLOADED = ROOT / 'assets/uploaded.json'
MIME = {'.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.mp3': 'audio/mpeg'}


_open, _sleep = urllib.request.urlopen, time.sleep   # 測試會換掉


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
            if e.code != 429 and e.code < 500: raise SystemExit(f'{method} {path} → {last}')
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = repr(e)
        print(f'{method} {path} 失敗（{last}），{10 * (t + 1)} 秒後重試', flush=True)
        _sleep(10 * (t + 1))
    raise SystemExit(f'{method} {path} 重試 {tries} 次仍失敗：{last}')


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


def upload_all(text):
    done = json.loads(UPLOADED.read_text()) if UPLOADED.exists() else {}
    for rel in sorted(set(re.findall(r'/files/assets/([\w./-]+\.(?:png|webp|jpg|mp3))', text))):
        f = ROOT / 'dist/assets' / rel   # build.main() 把 assets/ 與詩的 art、audio 鏡像到這裡
        key = f'{rel}@{int(f.stat().st_mtime)}'
        if key in done: continue
        body = {'name': 'tangshi_' + rel.replace('/', '_'), 'mimeType': MIME[f.suffix],
                'category': 'audio' if f.suffix == '.mp3' else 'image',
                'base64': base64.b64encode(f.read_bytes()).decode()}
        _, j = req('POST', '/media', body)
        done[key] = j['asset']['url']
        print('上傳', rel, '→', done[key], flush=True)
        UPLOADED.write_text(json.dumps(done, ensure_ascii=False, indent=1))
        time.sleep(2)
    latest = {}
    for k, url in done.items():
        latest[k.rsplit('@', 1)[0]] = url  # 同一檔多版本時取最後寫入的
    return latest


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
    urls = upload_all(text)
    for rel, url in urls.items():
        text = text.replace('/files/assets/' + rel, url)
    left = re.findall(r'/files/assets/[^"\\]+', text)
    if left: raise SystemExit(f'還有沒換掉的本機路徑：{left[:5]}')
    built = json.loads(text)

    etag, cur = req('GET')  # 上傳會改 media，重抓
    online = cur.get('project', cur)
    project = dict(online)
    if len(online.get('boards', [])) > len(built['boards']):
        raise SystemExit(f"線上有 {len(online['boards'])} 塊白板、本機只有 {len(built['boards'])} 塊；推送會蓋掉多的那塊，先確認")
    for k in ('boards', 'nodes', 'edges', 'variables', 'activeBoardId', 'name', 'description', 'languages'):
        project[k] = built[k]
    project['settings'] = merge_settings(online.get('settings'), built['settings'])
    try:
        req('PUT', '', {'project': project, 'summary': summary}, etag, tries=1)
    except SystemExit as e:   # PUT 可能其實寫進去了：讀回比對再決定要不要重送
        _, chk = req('GET'); chk = chk.get('project', chk)
        if len(chk['boards'][0]['nodes']) != len(built['boards'][0]['nodes']):
            print('PUT 失敗且線上未更新，重送一次：', e)
            et2, _ = req('GET'); req('PUT', '', {'project': project, 'summary': summary}, et2)

    _, back = req('GET')
    back = back.get('project', back)
    b0, w0 = back['boards'][0], built['boards'][0]
    def check(ok, msg):
        if not ok: raise SystemExit('讀回比對失敗：' + msg)
    check(len(b0['nodes']) == len(w0['nodes']), f"節點數 {len(b0['nodes'])} ≠ {len(w0['nodes'])}")
    check(len(b0['edges']) == len(w0['edges']), f"連線數 {len(b0['edges'])} ≠ {len(w0['edges'])}")
    check('tangshi-kit' in back['settings']['plugins'], '插件設定不見了')
    check(len(back['variables']) == len(built['variables']), '變數數量不符')
    print('推送完成，讀回比對通過：', len(b0['nodes']), '張卡、', len(b0['edges']), '條線')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '更新')
