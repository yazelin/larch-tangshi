"""生字資料：讀 poems/<詩>/vocab.json 並檢查。"""
import json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
TITLE = '過故人莊'
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
        if w not in TITLE + POEM: out.append(f'{w}: 不在詩裡')
    return out
