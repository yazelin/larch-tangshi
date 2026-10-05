"""劇情台詞配音：每句送 larch-tts-bridge（聲線、情緒照 poems/<詩>/voice.json），音檔存 audio/lines/<雜湊>.mp3。
bridge 會去頭尾靜音、統一響度（-18 LUFS）。檔名由講者、聲線、情緒、念出的文字決定，改了台詞才會重配；已存在的跳過。
    TTS_URL=http://127.0.0.1:8073/tts python3 src/line_audio.py
"""
import hashlib, json, os, pathlib, sys, time, urllib.error, urllib.request
import script
ROOT = pathlib.Path(__file__).resolve().parent.parent
POEM = ROOT / 'poems/guo-guren-zhuang'
OUT = POEM / 'audio/lines'
CFG = json.loads((POEM / 'voice.json').read_text())
URL = os.environ.get('TTS_URL', 'http://192.168.11.11:8072/tts')
KEY_FILE = pathlib.Path(os.environ.get('TTS_KEY_FILE', '~/.config/larch-tts/key')).expanduser()


def spoken(text):
    """畫面顯示原字，配音送替身字（只換列在 voice.json 的片段，一般的「斜斜地」不換）。"""
    for a, b in CFG['spoken']: text = text.replace(a, b)
    return text


def job(speaker, expr, text):
    who = speaker or '旁白'
    if who == '旁白': emotion = CFG['emotions']['旁白']
    elif expr: emotion = CFG['emotions'].get(expr, 'neutral')
    else: emotion = CFG.get('defaults', {}).get(who, 'neutral')   # 沒標表情時用角色的預設情緒
    say = spoken(text)
    voice = CFG['voices'][who]
    h = hashlib.sha256('\n'.join((who, voice, emotion, say)).encode()).hexdigest()[:16]
    return {'who': who, 'voice': voice, 'emotion': emotion, 'text': say, 'file': f'{h}.mp3'}


def all_jobs():
    s = script.load()
    out = [job(i['speaker'] if i['speaker'] != '旁白' else '', i['expr'], i['text'])
           for sc in s['scenes'] for i in sc['items'] if i['kind'] == 'line']
    out += [job(sp, '', tx) for lines in s['explain'].values() for sp, tx in lines]
    return out


def tts(j):
    h = {'Content-Type': 'application/json'}
    if KEY_FILE.exists(): h['X-API-Key'] = KEY_FILE.read_text().strip()
    body = json.dumps({'text': j['text'], 'voice': j['voice'], 'emotion': j['emotion'], 'format': 'mp3'}).encode()
    for t in range(5):   # Larch 寫入太頻繁會回 429（bridge 包成 502），等一下再試
        try:
            with urllib.request.urlopen(urllib.request.Request(URL, data=body, headers=h), timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 502 or t == 4: raise
            print('502，', 30 * (t + 1), '秒後重試：', e.read()[:120], flush=True)
            time.sleep(30 * (t + 1))


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = all_jobs()
    todo = [j for j in jobs if not (OUT / j['file']).exists()]
    print(f'{len(jobs)} 句，要配 {len(todo)} 句', flush=True)
    for n, j in enumerate(todo, 1):   # bridge 一次一句、全域鎖，依序跑
        (OUT / j['file']).write_bytes(tts(j))
        print(n, j['who'], j['emotion'], j['text'][:20], flush=True)
