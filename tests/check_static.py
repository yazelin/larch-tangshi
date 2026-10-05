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
    assert sc['items'][0] == {'kind': 'line', 'speaker': '孟浩然', 'text': '有人送信來了。'}
    assert sc['items'][1]['speaker'] == '旁白'
    assert sc['items'][2] == {'kind': 'vocab', 'word': '雞黍'} and sc['items'][3] == {'kind': 'follow', 'pair': 0}
    assert s['explain']['雞黍'] == [('故人', '你看，這一粒一粒黃黃的就是黍。')]

@test
def script_bad_directive():
    import script
    try: script.parse('# s1 x\n@不存在 1\n')
    except ValueError as e: assert '第 2 行' in str(e), e; return
    raise AssertionError('未知指令應該 raise ValueError')

if __name__ == '__main__': main()
