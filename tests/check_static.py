"""靜態檢查：python3 tests/check_static.py"""
import json, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
from run import test, main

@test
def link_with_condition():
    import cards
    b = {'edges': []}
    cards.link(b, 'a', 'b', cond=('last_ok', 'eq', False))
    c = b['edges'][0]['data']['condition']
    assert c['variable'] == 'last_ok' and c['value'] is False and c['conditions'][0]['op'] == 'eq', c

@test
def setvar_card():
    import cards
    n = cards.setvar('h1', '跳', [{'variable': 'hop', 'op': 'set', 'value': 1}])
    assert n['data']['type'] == 'setVariable' and n['data']['variableOps'][0]['variable'] == 'hop'

@test
def vocab_ok():
    import vocab
    v = vocab.load()
    assert len(v) == 23 and sum(e['core'] for e in v) == 12, (len(v), sum(e['core'] for e in v))
    assert vocab.problems(v) == [], vocab.problems(v)

@test
def vocab_problems_catch():
    import vocab
    bad = [{'id': 'x-1', 'word': '雞黍', 'zhuyin': 'ㄐㄧ', 'meaning': '', 'core': True},
           {'id': 'y', 'word': '不在詩裡', 'zhuyin': 'ㄅ ㄅ ㄅ ㄅ', 'meaning': '甲', 'core': False}]
    p = vocab.problems(bad)
    assert any('x-1' in s and 'id' in s for s in p) and any('注音' in s for s in p) \
        and any('meaning' in s for s in p) and any('不在詩裡' in s for s in p), p

@test
def poem_lines():
    import vocab
    assert vocab.LINES[5] == '把酒話桑麻' and len(vocab.LINES) == 8 and all(len(l) == 5 for l in vocab.LINES)

SAMPLE = '''# s1 故人具雞黍 | bg=gate
孟浩然：有人送信來了。
旁白：門口站著一個孩子。
@生字 雞黍
@跟念 0
# explain
## 雞黍
故人：你看，這一粒一粒黃黃的就是黍。
'''

@test
def script_parse():
    import script
    s = script.parse(SAMPLE)
    sc = s['scenes'][0]
    assert (sc['id'], sc['title'], sc['bg']) == ('s1', '故人具雞黍', 'gate'), sc
    assert sc['items'][0] == {'kind': 'line', 'speaker': '孟浩然', 'expr': '', 'text': '有人送信來了。'}
    assert sc['items'][1]['speaker'] == '旁白'
    assert sc['items'][2] == {'kind': 'vocab', 'word': '雞黍'} and sc['items'][3] == {'kind': 'follow', 'pair': 0}
    assert s['explain']['雞黍'] == [('故人', '你看，這一粒一粒黃黃的就是黍。')]

@test
def script_bad_directive():
    import script
    try: script.parse('# s1 x\n@不存在 1\n')
    except ValueError as e: assert '第 2 行' in str(e), e; return
    raise AssertionError('未知指令應該 raise ValueError')

@test
def variables_cover_core():
    import variables, vocab
    for e in vocab.load():
        if e['core']: assert f"got_{e['id']}" in variables.VARS, e['id']
    for k in ('last_ok', 'learned', 'stars', 'hop'): assert k in variables.VARS

@test
def card_node_gate_lists():
    import plugin
    n = plugin.card_node('vocab', 'n1', {'word': '郭'}, read=['got_guocheng', 'learned'], write=['got_guocheng', 'learned', 'last_ok'])
    d = n['data']
    assert d['pluginId'] == 'tangshi-kit' and d['pluginCardId'] == 'vocab'
    assert d['pluginWriteVars'] == ['got_guocheng', 'learned', 'last_ok'] and d['pluginFrame']['showButton'] is False
    assert '"word": "郭"' in d['pluginValues']['script'] and 'common.js' not in d['pluginHtml']

@test
def recite_plan_rules():
    import recite_plan, vocab
    r = recite_plan.plan(vocab.LINES)
    allc = ''.join(vocab.LINES)
    assert [len(x['hide']) for x in r] == [14, 27, 40], [len(x['hide']) for x in r]
    for x in r:
        hidden = {allc[i] for i in x['hide']}
        extra = [t for t in x['tiles'] if t not in hidden]
        assert len(extra) == 3, extra
        assert sorted(t for t in x['tiles'] if t in hidden) == sorted(allc[i] for i in x['hide'])
    assert recite_plan.plan(vocab.LINES) == r, '同 seed 要固定'

def _built():
    import build
    return build.build()

@test
def build_flow():
    p = _built()
    b = p['boards'][0]
    ids = {n['id'] for n in b['nodes']}
    for need in ('v-jishu', 'x-jishu', 'f-0', 'order', 'recite', 'summary', 'r-jishu'):
        assert need in ids, need
    out = lambda a: [e for e in b['edges'] if e['source'] == a]
    vj = out('v-jishu')
    assert any(e.get('data', {}).get('condition', {}).get('variable') == 'last_ok' and e['target'] == 'x-jishu' for e in vj), vj
    assert any('data' not in e for e in vj), '生字卡要有一條無條件的預設出口'
    assert [e['target'] for e in out('x-jishu')] == ['v-jishu'], '解釋完回到同一張生字卡'
    starts = [n for n in b['nodes'] if n['data'].get('start')]
    assert len(starts) == 1

@test
def every_node_reaches_end():
    p = _built(); b = p['boards'][0]
    nxt = {}
    for e in b['edges']: nxt.setdefault(e['source'], []).append(e['target'])
    def reach(start):
        seen, todo = set(), [start]
        while todo:
            x = todo.pop()
            if x in seen: continue
            seen.add(x); todo += nxt.get(x, [])
        return seen
    after = reach('summary')   # 結算之後的收尾台詞算終點
    for n in b['nodes']:
        assert n['id'] in after or 'summary' in reach(n['id']), f"{n['id']} 走不到結算"

@test
def gate_matches_script():
    import variables
    for n in _built()['boards'][0]['nodes']:
        d = n['data']
        if d.get('type') != 'plugin': continue
        s = json.loads(d['pluginValues']['script'])
        if d['pluginCardId'] == 'vocab' and s.get('quiz'):
            assert set(d['pluginWriteVars']) == {s['gotVar'], 'learned', 'last_ok'}, n['id']
            assert set(d['pluginReadVars']) == {s['gotVar'], 'learned'}, n['id']
        for v in d['pluginReadVars'] + d['pluginWriteVars']: assert v in variables.VARS, (n['id'], v)

@test
def vocab_cards_have_media():
    for n in _built()['boards'][0]['nodes']:
        d = n['data']
        if d.get('pluginCardId') == 'vocab':
            s = json.loads(d['pluginValues']['script'])
            assert s['img'], n['id']
            for o in s.get('options', []): assert o['img'], n['id']

@test
def plugin_html_unique_per_node():
    # 相鄰兩張插件卡的 pluginHtml 一字不差時，播放器不會重載 iframe，第二張卡沿用第一張的畫面（2026-10-05 實測）
    htmls = [n['data']['pluginHtml'] for n in _built()['boards'][0]['nodes'] if n['data'].get('type') == 'plugin']
    assert len(htmls) == len(set(htmls)), f'{len(htmls) - len(set(htmls))} 張插件卡的 HTML 跟別張重複'

@test
def script_covers_all_vocab():
    import script, vocab
    s = script.load()
    used = [i['word'] for sc in s['scenes'] for i in sc['items'] if i['kind'] == 'vocab']
    words = [e['word'] for e in vocab.load()]
    assert sorted(used) == sorted(words), set(words) ^ set(used)
    for e in vocab.load():
        if e['core']: assert s['explain'].get(e['word']), f"{e['word']} 沒有答錯解釋"
    follows = [i['pair'] for sc in s['scenes'] for i in sc['items'] if i['kind'] == 'follow']
    assert follows == [0, 1, 2, 3], follows

@test
def script_poem_quotes_exact():
    import script, vocab, re
    for sc in script.load()['scenes']:
        for i in sc['items']:
            if i['kind'] == 'line':
                for q in re.findall(r'「([^」]{5,})」', i['text']):
                    if any(c in q for c in '雞黍軒郭桑麻菊') and '，' in q:
                        assert q.rstrip('。') in vocab.POEM, f'詩句引錯：{q}'

@test
def script_expr_and_bg():
    import script
    s = script.parse('# s1 x | bg=gate\n孟浩然〔開心〕：好。\n@背景 cg-1\n旁白：看。\n')
    it = s['scenes'][0]['items']
    assert it[0] == {'kind': 'line', 'speaker': '孟浩然', 'expr': '開心', 'text': '好。'}, it[0]
    assert it[1] == {'kind': 'bg', 'key': 'cg-1'}, it[1]

@test
def stage_per_line():
    # 作者 2026-10-05 拍板：手機上四人擠不下，只站講話的人（置中）；旁白沿用上一位
    import build
    a = {'ch-meng-開心': 'M開', 'ch-meng-平常': 'M平', 'ch-ahe-平常': 'A平', 'ch-ahe-驚訝': 'A驚'}
    seen = []
    st0 = build.stage_for(('', ''), seen, a)
    st1 = build.stage_for(('孟浩然', '開心'), seen, a)
    st2 = build.stage_for(('阿禾', '驚訝'), seen, a)
    st3 = build.stage_for(('', ''), seen, a)
    assert st0 == [], '還沒有人開口前，旁白不站人'
    assert [(x['name'], x['url'], x['slot']) for x in st1] == [('孟浩然', 'M開', 'center')], st1
    assert [(x['name'], x['url']) for x in st2] == [('阿禾', 'A驚')], st2
    assert [(x['name'], x['url']) for x in st3] == [('阿禾', 'A平')], '旁白時沿用上一位、回到平常'
    assert st2[0]['loop'] == 'breathe'

@test
def cg_background_clears_stage():
    import art
    a = art.paths()
    cg = {a[f'cg-{i}'] for i in range(1, 6)}
    cards_on_cg = [n for n in _built()['boards'][0]['nodes'] if n['data'].get('type') == 'dialogue' and n['data'].get('background') in cg]
    assert len(cards_on_cg) >= 4, f'四聯各要有一張 CG 背景卡，現在 {len(cards_on_cg)}'
    for n in cards_on_cg:
        assert all(not l.get('stage', {}).get('actors') for l in n['data']['dialogueLines']), n['id']

@test
def title_and_cover():
    import art
    p = _built()
    assert p['name'] == '唐詩小旅行：過故人莊'
    assert p['description'].startswith('阿禾和小樂') and len(p['description']) < 1200
    a = art.paths()
    assert p['settings']['titleCoverImage'] == a['cg-5'] and p['settings']['projectThumbnail'] == a['cg-5']

if __name__ == '__main__': main()
