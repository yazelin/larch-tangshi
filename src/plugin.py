"""自製插件 tangshi-kit：生字、跟著念、排圖、背誦四張卡。產卡片節點、settings.plugins、manifest 與單卡測試專案。

    python3 src/plugin.py --test <card_id> [--preset '<json>'] [--patch '<json>']   # 產 dist/test-<card_id>.json
"""
import copy, json, pathlib, sys
import cards, recite_plan, variables, vocab

HERE = pathlib.Path(__file__).resolve().parent / 'plugin'
ROOT = HERE.parent.parent
PLUGIN_ID, VERSION, NAME, COLOR = 'tangshi-kit', '1.0.0', '唐詩小旅行', '#2f6b4f'
CARDS = {
    'vocab': {'name': '生字卡', 'presentation': 'fullscreen'},
    'follow': {'name': '跟著念', 'presentation': 'fullscreen'},
    'order': {'name': '四張圖排順序', 'presentation': 'fullscreen'},
    'recite': {'name': '背誦闖關', 'presentation': 'fullscreen'},
}
# 單卡測試用的資料：{'script', 'read', 'write', 'preset'}；script 也塞進卡片 HTML 當編輯器預覽的預設值
SAMPLES = {}
_PH = '/files/assets/placeholder/vocab.png'
SAMPLES['vocab'] = {
    'script': {'word': '雞黍', 'zhuyin': 'ㄐㄧ ㄕㄨˇ', 'meaning': '雞肉和黃米飯，招待客人的飯菜',
               'img': _PH, 'audio': '', 'quiz': True, 'retry': True,
               'gotVar': 'got_jishu', 'review': False, 'ask': '「雞黍」是什麼意思？',
               'options': [{'img': _PH, 'label': '雞肉和黃米飯', 'ok': True},
                           {'img': _PH, 'label': '一隻小雞', 'ok': False},
                           {'img': _PH, 'label': '白米飯', 'ok': False}]},
    'read': ['got_jishu', 'learned'], 'write': ['got_jishu', 'learned', 'last_ok']}
_CG = '/files/assets/placeholder/cg.png'
SAMPLES['order'] = {'script': {'items': [{'img': _CG, 'caption': f'{vocab.LINES[2*i]}，{vocab.LINES[2*i+1]}'} for i in range(4)],
                               'start': [2, 0, 3, 1]}, 'read': [], 'write': []}
SAMPLES['recite'] = {'script': {'lines': vocab.LINES, 'rounds': recite_plan.plan(vocab.LINES)}, 'read': [], 'write': ['stars']}
SAMPLES['follow'] = {'script': {'lines': ['故人具雞黍', '邀我至田家'], 'audio': '', 'marks': []}, 'read': [], 'write': []}


def html(card_id):
    src = (HERE / f'{card_id}.html').read_text()
    sample = '<script>window.SAMPLE=' + json.dumps(SAMPLES.get(card_id, {}).get('script', {}), ensure_ascii=False) + '</script>'
    return src.replace('<script src="common.js"></script>', sample + '<script>' + (HERE / 'common.js').read_text() + '</script>')


def card_node(card_id, node_id, script, read, write):
    # HTML 尾端加節點 id：相鄰兩張卡 HTML 一樣時，播放器不重載 iframe，第二張會沿用第一張的畫面
    c = CARDS[card_id]
    return {'id': node_id, 'type': 'story', 'position': cards._pos(), 'data': {
        'type': 'plugin', 'title': c['name'], 'text': '', 'pluginId': PLUGIN_ID, 'pluginCardId': card_id,
        'pluginName': NAME, 'pluginCardName': c['name'], 'pluginVersion': VERSION, 'pluginIcon': 'book',
        'pluginColor': COLOR, 'pluginHtml': html(card_id) + f'<!-- {node_id} -->', 'pluginPresentation': c['presentation'],
        'pluginValues': {'script': json.dumps(script, ensure_ascii=False)}, 'pluginAssets': [],
        'pluginReadVars': list(read), 'pluginWriteVars': list(write), 'pluginSkippable': False,
        'pluginFrame': {'showTitle': False, 'showButton': False}, 'platforms': ['web']}}


def settings_entry():
    return {'enabled': True, 'playback': {'version': VERSION, 'permissions': ['variables:read'], 'defaults': {}, 'huds': []}}


def manifest():
    """給 larch_save_plugin_draft 的完整 manifest。"""
    return {'id': PLUGIN_ID, 'name': NAME, 'version': VERSION, 'author': '林亞澤',
            'description': '唐詩教材用：生字卡、跟著念、四張圖排順序、背誦闖關。內容全由卡片參數 script（JSON）傳入。',
            'categories': ['card'], 'icon': 'book',
            'permissions': ['variables:read', 'variables:write', 'assets:read', 'flow:control'],
            'cards': [{'id': k, 'name': c['name'], 'description': c['name'], 'icon': 'book', 'color': COLOR,
                       'presentation': c['presentation'],
                       'fields': [{'key': 'script', 'kind': 'longText', 'label': '內容（JSON）'}],
                       'html': html(k)} for k, c in CARDS.items()], 'huds': []}


def test_project(card_id, script, read, write, preset=None):
    import build
    p = build.load_skeleton()
    b = p['boards'][0]
    b['nodes'], b['edges'] = [], []
    p['nodes'], p['edges'] = b['nodes'], b['edges']
    p['variables'] = variables.project_variables()
    for v in p['variables']:
        if v['name'] in (preset or {}): v['defaultValue'] = preset[v['name']]
    p['settings']['plugins'][PLUGIN_ID] = settings_entry()
    b['nodes'].append(cards.dialogue('t-start', '測試開始', ['測試：' + card_id], start=True))
    b['nodes'].append(card_node(card_id, 't-card', script, read, write))
    shown = ' '.join(f'{k}={{{{{k}}}}}' for k in write)
    b['nodes'].append(cards.dialogue('t-result', '結果', ['RESULT ' + shown]))
    cards.link(b, 't-start', 't-card'); cards.link(b, 't-card', 't-result')
    return p


if __name__ == '__main__':
    if sys.argv[1:2] == ['--test']:
        import build
        cid = sys.argv[2]
        s = copy.deepcopy(SAMPLES[cid])
        args = dict(zip(sys.argv[3::2], sys.argv[4::2]))
        if '--preset' in args: s['preset'] = json.loads(args['--preset'])
        if '--patch' in args: s['script'].update(json.loads(args['--patch']))
        out = ROOT / f'dist/test-{cid}.json'
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(test_project(cid, s['script'], s['read'], s['write'], s.get('preset')), ensure_ascii=False))
        build.mirror_assets(out.parent / 'assets')
        print('wrote', out)
