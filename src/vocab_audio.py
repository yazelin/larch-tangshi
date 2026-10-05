"""生字與跟念音檔：送 larch-tts-bridge（.11:8072），文字用 vocab.json 的 tts 替身字。已存在的檔跳過。
    python3 src/vocab_audio.py
"""
import json, os, pathlib, urllib.request
import vocab
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'poems/guo-guren-zhuang/audio'
URL = os.environ.get('TTS_URL', 'http://192.168.11.11:8072/tts')
VOICE = os.environ.get('TTS_VOICE', 'Chinese (Mandarin)_Wise_Women')
KEY_FILE = pathlib.Path(os.environ.get('TTS_KEY_FILE', '~/.config/larch-tts/key')).expanduser()
SUBS = {'斜': '霞', '郭': '鍋', '還': '孩'}   # 跟念整句用的替身


def tts(text, dst):
    if dst.exists(): return
    dst.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps({'text': text, 'voice': VOICE, 'format': 'mp3'}).encode()
    h = {'Content-Type': 'application/json'}
    if KEY_FILE.exists(): h['X-API-Key'] = KEY_FILE.read_text().strip()   # bridge 發過金鑰之後就一定要帶
    r = urllib.request.Request(URL, data=body, headers=h)
    with urllib.request.urlopen(r, timeout=300) as resp: dst.write_bytes(resp.read())
    print('wrote', dst, flush=True)


if __name__ == '__main__':
    # bridge 一次一句、全域鎖，依序跑
    for e in vocab.load(): tts(e['tts'] + '。', OUT / 'vocab' / f"{e['id']}.mp3")
    for i in range(4):
        line = '，'.join(vocab.LINES[2 * i:2 * i + 2]) + '。'
        tts(''.join(SUBS.get(c, c) for c in line), OUT / 'follow' / f'{i}.mp3')
