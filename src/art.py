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
