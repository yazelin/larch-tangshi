"""美術與音檔路徑：正式檔在 poems/<詩>/art|audio，不在就退回佔位圖（音檔退回空字串）。"""
import pathlib
import vocab
ROOT = pathlib.Path(__file__).resolve().parent.parent
POEM = ROOT / 'poems/guo-guren-zhuang'
BGS = ('study', 'gate', 'road', 'room', 'fence')
CAST = {'阿禾': 'ahe', '小樂': 'xiaole', '孟浩然': 'meng', '故人': 'guren'}
EXPRS = ('平常', '開心', '驚訝', '想事情')


def _pick(rel, fallback):
    for ext in ('.webp', '.png', '.jpg', '.mp3'):
        f = POEM / (rel + ext)
        if f.exists(): return '/files/assets/' + str(f.relative_to(POEM))
    return fallback


def paths():
    a = {f'bg-{b}': _pick(f'art/bg/{b}', '/files/assets/placeholder/bg.png') for b in BGS}
    a.update({f'cg-{i}': _pick(f'art/cg/{i}', '/files/assets/placeholder/cg.png') for i in range(1, 6)})
    for cid in CAST.values():   # 立繪：沒有正式檔就不放（不給佔位圖，舞台空著）
        for ex in EXPRS:
            u = _pick(f'art/char/{cid}-{ex}', '')
            if u: a[f'ch-{cid}-{ex}'] = u
    for e in vocab.load():
        a[f"v-{e['id']}"] = _pick(f"art/vocab/{e['id']}", '/files/assets/placeholder/vocab.png')
        a[f"a-{e['id']}"] = _pick(f"audio/vocab/{e['id']}", '')
    a.update({f'f-{i}': _pick(f'audio/follow/{i}', '') for i in range(4)})
    return a
