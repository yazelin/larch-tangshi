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

if __name__ == '__main__': main()
