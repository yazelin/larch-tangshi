"""全專案變數只在這裡定義：名字 → (型別, 預設值, 標籤)。got_<id>：-1 沒看過、0 第一次答錯、1 第一次答對、2 複習時答對。"""
import vocab

VARS = {
    'last_ok': ('boolean', False, '剛才那題答對'),
    'learned': ('number', 0, '學會的字數'),
    'stars': ('number', 0, '背誦星星'),
    'hop': ('number', 0, '複習進度'),
}
for _e in vocab.load():
    if _e['core']: VARS[f"got_{_e['id']}"] = ('number', -1, f"生字：{_e['word']}")


def project_variables():
    return [{'id': k, 'name': k, 'label': lab, 'type': t, 'defaultValue': d} for k, (t, d, lab) in VARS.items()]
