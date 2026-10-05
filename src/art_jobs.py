"""產背景與生字小圖：python3 src/art_jobs.py [bg|vocab]。走 codex-imagegen（本機 codex），已存在的跳過。
畫面內容依 poems/guo-guren-zhuang/考證.md 的「畫面要點」。產完轉成 webp 縮小再進版控。"""
import pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
ART = ROOT / 'poems/guo-guren-zhuang/art'
GEN = pathlib.Path('~/.claude/skills/codex-imagegen/codex-imagegen.sh').expanduser()
STYLE = ("Style: soft watercolor children's picture-book illustration, gentle pencil outlines, warm natural palette, "
         "Tang dynasty Chinese countryside in early autumn. Simple rural farmhouses with thatched roofs and earthen walls, "
         "no red pillars, no palace architecture. No text, no letters, no watermark.")
BG = {
    'study': 'A quiet modern elementary school library after class, wooden shelves, warm late-afternoon light, one old book on a table glowing softly. No people.',
    'gate': 'A Tang dynasty farmhouse with a thick thatched roof and earthen yellow walls, a low gate and fence woven from bamboo and twigs, a packed dirt path leading to the gate, trees with a few yellowing leaves. No people.',
    'road': 'View from a small earthen hill: a village of thatched farmhouses encircled by a ring of green trees; beyond the fields in the distance a long earthen outer city wall; behind it a blue-green mountain slope lying diagonally across the horizon. No people.',
    'room': 'Inside a simple Tang dynasty farmhouse: earthen walls, a low wooden table with pottery bowls, a wooden window pushed open; through the window a flat yard, half of it rows of green vegetable beds, half of it smooth packed yellow earth with grain spread out to dry and a bamboo rake leaning nearby. No people.',
    'fence': 'A bamboo fence beside a thatched farmhouse at golden sunset, many chrysanthemum plants along the fence with tight green buds just starting to show yellow. Trees have only leaves: no fruit, no berries anywhere (early autumn). No people.',
}
VOCAB = {
    'guo': 'A traveler in a plain Tang robe arriving at a farmhouse bamboo gate, seen from behind, visiting.',
    'guren': 'Two middle-aged Tang men in simple clothes greeting each other warmly with cupped hands, old friends reunited, small figures.',
    'zhuang': 'A small rural village of thatched farmhouses among trees and fields.',
    'ju': 'Hands setting out pottery dishes on a low wooden table, preparing a meal.',
    'jishu': 'A pottery plate of stewed chicken and a pottery bowl of pale yellow-white sticky small round millet grains, steaming. Not white rice.',
    'yao': 'A smiling Tang farmer at his gate waving his hand to invite a guest in.',
    'zhi': 'A dirt path with footprints ending right at a farmhouse door, arriving.',
    'tianjia': 'A thatched farmhouse next to green crop fields.',
    'he': 'Top-down view of a small village completely encircled by a ring of round green trees.',
    'guocheng': 'A long earthen outer city wall with fields outside it.',
    'xia': 'A blue-green mountain slope lying diagonally, slanting across the picture.',
    'xuan': 'An open wooden window with its shutter pushed outward.',
    'mian': 'A wooden window directly facing a flat farmyard, seen from inside the room.',
    'chang': 'A flat packed-earth threshing ground with golden grain spread out to dry and a bamboo rake.',
    'pu': 'A vegetable garden with neat rows of green leafy vegetables.',
    'ba': 'A hand holding a small pottery wine cup.',
    'hua': 'Two Tang men sitting at a low table chatting happily, small figures.',
    'sangma': 'A mulberry branch with broad serrated leaves and a few white silkworms, beside tall green hemp stalks.',
    'daidao': 'Chrysanthemum plants by a bamboo fence with tight closed buds, waiting to bloom.',
    'chongyang': 'People climbing a hill in autumn, with yellow chrysanthemums and a small wine jar on a rock at the top, small figures.',
    'hailai': 'Footprints walking back to the same farmhouse bamboo gate, with fallen autumn leaves, returning again.',
    'jiu': 'A Tang man in a plain robe bending close to look at blooming yellow chrysanthemums by a fence.',
    'juhua': 'Blooming yellow chrysanthemum flowers by a bamboo fence.',
}

# 立繪：四人共用青色幕（綠會吃掉小樂的裙子、洋紅離阿禾的紅鞋太近），之後用 cutout 去背
KEY = '#00FFFF'
CAST = {'阿禾': 'ahe', '小樂': 'xiaole', '孟浩然': 'meng', '故人': 'guren'}
EXPRS = {'平常': 'calm neutral friendly expression, arms relaxed',
         '開心': 'big happy smile, one hand slightly raised in a cheerful gesture',
         '驚訝': 'surprised expression with wide eyes and open mouth, both hands raised a little',
         '想事情': 'thinking expression, looking slightly up, one finger touching the chin'}
CHAR_RULES = (f'Full body standing, facing slightly toward the viewer. Background: one flat solid pure cyan {KEY} color '
              'filling the whole canvas, even lighting, crisp edges. No shadow, no ground, no gradient, no vignette, '
              'no reflection, the character does not touch any edge of the picture. Portrait 2:3.')
# 劇情 CG：present 是在場角色，產圖時一律附上這些人的定錨（CG 一定帶在場角色定錨）
CG = {
    1: {'present': ['故人', '孟浩然', '阿禾', '小樂'],
        'scene': 'At the bamboo gate of a thatched farmhouse, the old farmer (image 1) warmly waves the poet (image 2) and the two children (image 3, image 4) inside. Through the open door a low table shows a plate of stewed chicken and a pottery bowl of pale yellow sticky millet.'},
    2: {'present': ['孟浩然', '故人', '阿禾', '小樂'],
        'scene': 'On a small earthen hill, the poet (image 1), the old farmer (image 2) and the two children (image 3, image 4) are seen from behind looking down at a village encircled by a ring of green trees; far away a long earthen outer city wall, and behind it a blue-green mountain slope lying diagonally.'},
    3: {'present': ['孟浩然', '故人', '阿禾', '小樂'],
        'scene': 'Inside a simple farmhouse by a wooden window pushed open: the poet (image 1) and the old farmer (image 2) sit at a low table, each holding a small pottery wine cup in one hand, chatting happily; the two children (image 3, image 4) eat from pottery bowls. Through the window: half green vegetable beds, half flat packed earth with drying grain; mulberry trees outside.'},
    4: {'present': ['孟浩然', '故人', '阿禾', '小樂'],
        'scene': 'At golden sunset beside a bamboo fence lined with chrysanthemum plants in tight buds, the poet (image 1) and the old farmer (image 2) smile and make a promise to meet again; the two children (image 3, image 4) stand next to them looking at the buds.'},
    5: {'present': ['阿禾', '小樂'],
        'scene': 'In a quiet modern school library, the two children (image 1, image 2) open an old glowing book; golden Chinese-style brush strokes swirl up out of the pages around them like wind. Leave calm empty space in the upper third for a title.'},
}
ANCHOR = lambda name: str(ROOT / 'canon/角色' / f'{name}.webp')


def gen(prompt, out, refs=()):
    if out.with_suffix('.webp').exists() or out.exists(): return
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['bash', str(GEN), prompt, str(out), *refs], check=True, stdin=subprocess.DEVNULL)
    print('wrote', out, flush=True)


if __name__ == '__main__':
    kind = sys.argv[1]
    if kind == 'bg':
        for k, p in BG.items(): gen(f'{p} Wide landscape 16:9. {STYLE}', ART / 'bg' / f'{k}.png')
    if kind == 'vocab':
        for k, p in VOCAB.items(): gen(f'{p} Square 1:1 icon-like composition, single clear subject centered, plain cream background. {STYLE}', ART / 'vocab' / f'{k}.png')
    if kind == 'char':
        for name, cid in CAST.items():
            for ex, desc in EXPRS.items():
                gen(f'The exact same character as image 1: same face, hair, outfit, colors and proportions. {desc}. {CHAR_RULES} '
                    "Style: soft watercolor children's picture-book illustration, gentle pencil outlines. No text, no watermark.",
                    ART / 'char' / 'raw' / f'{cid}-{ex}.png', [ANCHOR(name)])
    if kind == 'cg':
        for i, c in CG.items():
            assert c['present'] and all(pathlib.Path(ANCHOR(n)).exists() for n in c['present']), f'CG {i} 在場角色定錨缺'
            who = '; '.join(f'image {k + 1} is {n}' for k, n in enumerate(c['present']))
            gen(f"{c['scene']} Keep every character exactly as in their reference image ({who}): same faces, hair, outfits and colors; each person appears once. "
                f'Wide landscape 16:9. {STYLE}', ART / 'cg' / f'{i}.png', [ANCHOR(n) for n in c['present']])
