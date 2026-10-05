"""push.py 的 PUT 失敗處理：python3 tests/unit_push.py"""
import os, sys, tempfile, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
k = tempfile.NamedTemporaryFile('w', delete=False); k.write('test-key'); k.close()
os.environ['LARCH_KEY_FILE'] = k.name
import push
from run import test, main

BOARD = {'nodes': [{'id': 'a', 'data': {'type': 'dialogue', 'dialogueLines': [{'text': '新'}]}}], 'edges': []}
OLD = {'nodes': [{'id': 'a', 'data': {'type': 'dialogue', 'dialogueLines': [{'text': '舊'}]}}], 'edges': []}


def fake(put_status, online_after):
    calls = []
    def req(method, path='', body=None, etag=None, tries=6):
        calls.append(method)
        if method == 'PUT':
            if put_status: raise push.HttpFail(f'PUT → {put_status}', put_status)
            return None, {}
        return '"9"', {'project': {'boards': [online_after]}}
    return req, calls


def run(put_status, online_after):
    req, calls = fake(put_status, online_after)
    push.req = req
    try: push.put_project({'boards': [BOARD]}, 'x', '"8"', BOARD); return 'ok', calls
    except SystemExit as e: return str(e), calls


@test
def conflict_412_aborts_without_resend():
    msg, calls = run(412, OLD)
    assert '網頁' in msg and calls.count('PUT') == 1, (msg, calls)

@test
def client_error_400_aborts():
    msg, calls = run(400, OLD)
    assert msg != 'ok' and calls.count('PUT') == 1, (msg, calls)

@test
def server_error_but_landed_is_ok():
    msg, calls = run(502, BOARD)
    assert msg == 'ok', msg

@test
def server_error_not_landed_aborts_without_resend():
    msg, calls = run(502, OLD)
    assert msg != 'ok' and calls.count('PUT') == 1, (msg, calls)

@test
def content_key_sees_text_change():
    assert push.content_key(BOARD) != push.content_key(OLD)

@test
def cdn_url_maps_repo_paths():
    u = push.cdn_url('art/bg/road.webp', 'abc123')
    assert u == 'https://cdn.jsdelivr.net/gh/yazelin/larch-tangshi@abc123/poems/guo-guren-zhuang/art/bg/road.webp', u
    assert push.cdn_url('placeholder/cg.png', 'abc123').endswith('@abc123/assets/placeholder/cg.png')
    assert push.cdn_url('audio/lines/x.mp3', 'abc123').endswith('/poems/guo-guren-zhuang/audio/lines/x.mp3')

def fake_git(status='', pushed=True):
    def g(*a):
        if a[0] == 'rev-parse': return 'head999\n'
        if a[0] == 'status': return status
        if a[0] == 'branch': return '  origin/main\n' if pushed else ''
        if a[0] == 'log': return {'poems/guo-guren-zhuang/art/bg/road.webp': 'aaa111\n', 'assets/placeholder/cg.png': 'bbb222\n'}[a[-1]]
        raise AssertionError(a)
    return g

@test
def to_cdn_pins_each_file_to_its_last_change():
    # 每個檔釘在自己最後改動的 commit：沒改的檔網址不變，jsDelivr 快取一直熱
    push._git = fake_git()
    out = push.to_cdn('{"a": "/files/assets/art/bg/road.webp", "b": "/files/assets/placeholder/cg.png"}')
    assert '@aaa111/poems/guo-guren-zhuang/art/bg/road.webp' in out and '@bbb222/assets/placeholder/cg.png' in out, out
    assert 'head999' not in out

@test
def to_cdn_refuses_uncommitted_or_unpushed():
    text = '{"a": "/files/assets/art/bg/road.webp"}'
    push._git = fake_git(status=' M poems/guo-guren-zhuang/art/bg/road.webp\n')
    try: push.to_cdn(text); raise AssertionError('有沒 commit 的素材要擋')
    except SystemExit as e: assert 'commit' in str(e)
    push._git = fake_git(pushed=False)
    try: push.to_cdn(text); raise AssertionError('commit 沒推上 GitHub 要擋')
    except SystemExit as e: assert 'GitHub' in str(e)

@test
def prewarm_purges_cached_404():
    # jsDelivr 會把冷抓失敗的 404 快取起來（檔案其實在）；預熱遇到 404 先 purge 再抓
    import io, urllib.error
    calls = []
    class R(io.BytesIO):
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
    def fake_open(req, timeout=0):
        u = req.full_url; calls.append(u)
        if u.startswith('https://purge.jsdelivr.net/'): return R(b'{}')
        if sum(1 for c in calls if c == u) == 1 and u.endswith('x.mp3'): raise urllib.error.HTTPError(u, 404, 'nf', {}, io.BytesIO(b''))
        return R(b'ok')
    orig = push._open; push._open = fake_open
    try: push.prewarm('"https://cdn.jsdelivr.net/gh/yazelin/larch-tangshi@aaa/poems/x.mp3"')
    finally: push._open = orig
    assert any(c.startswith('https://purge.jsdelivr.net/gh/yazelin/larch-tangshi@aaa/poems/x.mp3') for c in calls), calls

if __name__ == '__main__': main()
