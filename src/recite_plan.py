"""背誦三關：遮哪些字、給哪些字塊。用固定 seed，每次建置結果一樣。"""
import math, random
DECOYS = '春夏秋冬日月山水風雲花草'


def plan(lines, seed=7):
    allc = ''.join(lines)
    rng = random.Random(seed)
    order = list(range(len(allc)))
    rng.shuffle(order)
    out = []
    for frac in (1 / 3, 2 / 3, 1):
        hide = sorted(order[:math.ceil(len(allc) * frac)])
        hidden = {allc[i] for i in hide}
        decoys = [c for c in DECOYS if c not in hidden]   # 干擾字不能跟本關要填的字重複
        tiles = [allc[i] for i in hide] + rng.sample(decoys, 3)
        rng.shuffle(tiles)
        out.append({'hide': hide, 'tiles': tiles})
    return out
