"""組出 dist/project.json：骨架＋劇本對話卡＋tangshi-kit 插件卡＋有條件連線。"""
import json, os, pathlib, random, shutil
import art, cards, plugin, recite_plan, script, variables, vocab
ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT_ID = 'project-ac006859-4f72-4956-a83e-ddc2ed9a1c0a'


def load_skeleton():
    return json.loads((ROOT / 'skeleton/project.json').read_text())


def vocab_script(e, a, entries, review=False):
    s = {'word': e['word'], 'zhuyin': e['zhuyin'], 'meaning': e['meaning'], 'img': a[f"v-{e['id']}"],
         'audio': a[f"a-{e['id']}"], 'quiz': e['core'], 'retry': not review, 'review': review,
         'gotVar': f"got_{e['id']}", 'ask': f"「{e['word']}」是什麼意思？"}
    if e['core']:
        rng = random.Random(e['id'])                   # 干擾選項：其他生字的圖與解釋，每次建置一樣
        others = rng.sample([o for o in entries if o['id'] != e['id']], 2)
        opts = [{'img': a[f"v-{e['id']}"], 'label': e['meaning'], 'ok': True}] + \
               [{'img': a[f"v-{o['id']}"], 'label': o['meaning'], 'ok': False} for o in others]
        rng.shuffle(opts)
        s['options'] = opts
    return s


def vocab_node(e, a, entries, node_id, review=False):
    s = vocab_script(e, a, entries, review)
    if e['core']:
        g = f"got_{e['id']}"
        return plugin.card_node('vocab', node_id, s, read=[g, 'learned'], write=[g, 'learned', 'last_ok'])
    return plugin.card_node('vocab', node_id, s, read=[], write=[])

SLOT = {'阿禾': 'farLeft', '小樂': 'left', '孟浩然': 'right', '故人': 'farRight'}


def stage_for(who, seen, a):
    """一句台詞的站位：這一幕到這句為止開過口的人都在台上，講話的人換成他標的表情。seen 會被更新。"""
    sp, expr = who
    if sp in SLOT and sp not in seen: seen.append(sp)
    actors = []
    for name in seen:
        ex = expr if (name == sp and expr) else '平常'
        url = a.get(f'ch-{art.CAST[name]}-{ex}') or a.get(f'ch-{art.CAST[name]}-平常')
        if url: actors.append({'id': f'actor-{art.CAST[name]}', 'url': url, 'name': name, 'slot': SLOT[name],
                               'scale': 0.96, 'offsetX': 0, 'offsetY': 0, 'enter': 'fade', 'loop': 'breathe'})
    return actors


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
    entries = vocab.load()
    by_word = {e['word']: e for e in entries}
    N = board['nodes'].append
    L = lambda x, y, **k: cards.link(board, x, y, **k)
    st = {'prev': None, 'first': True}
    core_order = []

    def chain(node_id):
        if st['prev']: L(st['prev'], node_id)
        st['prev'] = node_id

    for scene in sc['scenes']:
        bg = a.get(f"bg-{scene['bg']}", '')
        buf, k, seen, on_cg = [], [0], [], [False]

        def flush():
            if not buf: return
            nid = f"{scene['id']}-{k[0]}"; k[0] += 1
            sp = lambda i: i['speaker'] if i['speaker'] != '旁白' else ''
            # 背景是 CG 時舞台清空，不然立繪會擋住畫面
            stages = [[] if on_cg[0] else stage_for((sp(i), i['expr']), seen, a) for i in buf]
            N(cards.dialogue(nid, scene['title'], [(sp(i), i['text']) for i in buf],
                             bg=bg, start=st['first'], stages=stages))
            st['first'] = False; buf.clear()
            chain(nid)

        for it in scene['items']:
            if it['kind'] == 'line': buf.append(it); continue
            flush()
            if it['kind'] == 'bg':
                bg = a[it['key']]; on_cg[0] = it['key'].startswith('cg-'); continue
            if it['kind'] == 'vocab':
                e = by_word[it['word']]
                vid = f"v-{e['id']}"
                N(vocab_node(e, a, entries, vid))
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
                    N(vocab_node(e, a, entries, rid, review=True))
                    L(hid, rid, cond=(f"got_{e['id']}", 'eq', 0))
                    L(rid, f'h-{n + 1}' if n + 1 < len(core_order) else 'h-end')
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
