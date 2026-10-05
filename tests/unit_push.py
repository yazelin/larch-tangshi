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

if __name__ == '__main__': main()
