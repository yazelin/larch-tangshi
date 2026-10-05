"""組出 dist/project.json：骨架＋劇本對話卡＋tangshi-kit 插件卡＋有條件連線。"""
import json, os, pathlib, random, re, shutil, subprocess
import art, cards, line_audio, plugin, recite_plan, script, variables, vocab
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

def follow_marks(url):
    """跟念音檔每個字的起點（秒）：抓最長的一段靜音當逗號停頓，前五字平均分在停頓前、後五字分在停頓後。
    沒有音檔或抓不到停頓就回 []，卡片會改用音檔長度平均分。"""
    if not url: return []
    f = ROOT / 'poems/guo-guren-zhuang' / url.removeprefix('/files/assets/')
    out = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(f), '-af', 'silencedetect=noise=-35dB:d=0.12', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    dur = float(re.search(r'Duration: (\d+):(\d+):([\d.]+)', out).group(3))
    gaps = [(float(a), float(b)) for a, b in re.findall(r'silence_start: ([\d.]+).*?silence_end: ([\d.]+)', out, re.S)]
    gaps = [g for g in gaps if 0.3 * dur < g[0] < 0.7 * dur]
    if not gaps: return []
    p0, p1 = max(gaps, key=lambda g: g[1] - g[0])
    return [round(p0 * i / 5, 3) for i in range(5)] + [round(p1 + (dur - p1) * i / 5, 3) for i in range(5)]


def voiced(node, who):
    """有配好音檔的台詞接上 voiceUrl，卡片打開 voiceMode（線上播放器只看卡片層這個欄位）。who：每句 (講者, 表情)。"""
    d = node['data']
    for line, (sp, ex) in zip(d['dialogueLines'], who):
        f = line_audio.job(sp, ex, line['text'])['file']
        if (line_audio.OUT / f).exists(): line['voiceUrl'] = '/files/assets/audio/lines/' + f
    if any(l.get('voiceUrl') for l in d['dialogueLines']): d['voiceMode'] = 'ai'
    return node


def stage_for(who, seen, a):
    """一句台詞的站位：只站講話的人（置中，換成他標的表情）；旁白時沿用上一位、回到平常。
    作者 2026-10-05 拍板：手機直式畫面四人全身擠不下。seen 記這一幕最後開口的人。"""
    sp, expr = who
    if sp in art.CAST: seen[:] = [sp]
    else: expr = ''
    if not seen: return []
    name = seen[0]
    cid = art.CAST[name]
    url = a.get(f'ch-{cid}-{expr or "平常"}') or a.get(f'ch-{cid}-平常')
    if not url: return []
    return [{'id': f'actor-{cid}', 'url': url, 'name': name, 'slot': 'center',
             'scale': 0.96, 'offsetX': 0, 'offsetY': 0, 'enter': 'fade', 'loop': 'breathe'}]


def build():
    p = load_skeleton()
    board = p['boards'][0]
    board['nodes'], board['edges'] = [], []
    p['nodes'], p['edges'] = board['nodes'], board['edges']
    p['variables'] = variables.project_variables()
    p['settings']['plugins'][plugin.PLUGIN_ID] = plugin.settings_entry()
    p['settings'].update({'stageFit': 'auto', 'keepActorsInFrame': False, 'cgGalleryEnabled': False})
    a = art.paths()
    p['name'] = '唐詩小旅行：過故人莊'
    p['description'] = (ROOT / 'poems/guo-guren-zhuang/簡介.md').read_text().strip()
    p['settings']['titleCoverImage'] = p['settings']['projectThumbnail'] = a['cg-5']   # 開場那張，上方留了標題空間
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
            N(voiced(cards.dialogue(nid, scene['title'], [(sp(i), i['text']) for i in buf],
                             bg=bg, start=st['first'], stages=stages), [(sp(i), i['expr']) for i in buf]))
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
                    N(voiced(cards.dialogue(xid, f"再說一次：{e['word']}", sc['explain'][e['word']], bg=bg),
                             [(spk, '') for spk, _ in sc['explain'][e['word']]]))
                    L(vid, xid, cond=('last_ok', 'eq', False))
                    L(xid, vid)
            elif it['kind'] == 'follow':
                i = it['pair']
                fid = f'f-{i}'
                N(plugin.card_node('follow', fid, {'lines': vocab.LINES[2 * i:2 * i + 2], 'audio': a[f'f-{i}'], 'marks': follow_marks(a[f'f-{i}'])}, [], []))
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
