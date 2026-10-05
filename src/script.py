"""劇本解析。格式：
# <場景id> <標題> | bg=<背景鍵>     開新場景（bg 可省）
講者：台詞 或 講者〔表情〕：台詞     台詞；沒有「：」的行算旁白
@生字 <詞>  @跟念 <0-3>  @排圖  @複習  @背誦  @結算  @背景 <鍵>（例如 cg-1，之後的台詞換這張背景）
# explain 之後用 ## <詞> 分段，寫答錯時的解釋台詞
空行與 <!-- --> 註解略過。
"""
import pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
SIMPLE = {'@排圖': 'order', '@複習': 'review', '@背誦': 'recite', '@結算': 'summary'}


def parse(text):
    scenes, explain, cur, word = [], {}, None, None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('<!--'): continue
        if line.startswith('# '):
            head, _, opt = line[2:].partition('|')
            sid, _, title = head.strip().partition(' ')
            if sid == 'explain': cur = 'explain'; continue
            bg = re.search(r'bg=(\S+)', opt)
            cur = {'id': sid, 'title': title.strip(), 'bg': bg.group(1) if bg else '', 'items': []}
            scenes.append(cur); continue
        if cur == 'explain':
            if line.startswith('## '): word = line[3:].strip(); explain[word] = []; continue
            sp, _, tx = line.partition('：')
            explain[word].append((sp, tx) if tx else ('', sp)); continue
        if cur is None: raise ValueError(f'第 {n} 行：還沒有場景標題')
        if line.startswith('@'):
            cmd, _, arg = line.partition(' ')
            if cmd == '@生字': cur['items'].append({'kind': 'vocab', 'word': arg.strip()})
            elif cmd == '@跟念': cur['items'].append({'kind': 'follow', 'pair': int(arg)})
            elif cmd == '@背景': cur['items'].append({'kind': 'bg', 'key': arg.strip()})
            elif cmd in SIMPLE: cur['items'].append({'kind': SIMPLE[cmd]})
            else: raise ValueError(f'第 {n} 行：不認得的指令 {cmd}')
            continue
        sp, _, tx = line.partition('：')
        m = re.fullmatch(r'(.+?)〔(.+)〕', sp) if tx else None
        if m: sp, expr = m.group(1), m.group(2)
        else: expr = ''
        cur['items'].append({'kind': 'line', 'speaker': sp if tx else '旁白', 'expr': expr, 'text': tx or sp})
    return {'scenes': scenes, 'explain': explain}


def load(poem='guo-guren-zhuang'):
    return parse((ROOT / 'poems' / poem / 'script.md').read_text())
