"""立繪：raw/*.png（青色幕）→ 去背 → 裁到人物外框 → 縮到固定身高 → 腳底對齊放進同尺寸畫布 → webp。
同一個角色換表情不會忽大忽小；大人和小孩的身高比例固定。python3 src/standees.py
縮放在 premultiplied alpha 下做，縮完再 despill 一次（cutout skill 的規矩）。"""
import pathlib, subprocess, sys, tempfile
import numpy as np
from PIL import Image
ROOT = pathlib.Path(__file__).resolve().parent.parent
CHAR = ROOT / 'poems/guo-guren-zhuang/art/char'
CUT = pathlib.Path('~/.claude/skills/cutout/cutout.py').expanduser()
KEY = '#00FFFF'
KEYS = {'ahe': '#00FF00'}   # 跟 art_jobs.KEYS 一致：阿禾用綠幕
W, H, FOOT = 1000, 1500, 30
HEIGHT = {'ahe': 1020, 'xiaole': 960, 'meng': 1420, 'guren': 1360}   # 畫布裡的人物身高（px）


def resize_premul(im, w, h):
    a = np.asarray(im, np.float32); al = a[..., 3:4] / 255.0
    pre = np.concatenate([a[..., :3] * al, a[..., 3:4]], -1)
    r = np.asarray(Image.fromarray(pre.round().astype(np.uint8), 'RGBA').resize((w, h), Image.LANCZOS), np.float32)
    al2 = np.clip(r[..., 3:4] / 255.0, 1e-4, 1.0)
    rgb = np.clip(r[..., :3] / al2, 0, 255)
    return Image.fromarray(np.concatenate([rgb, r[..., 3:4]], -1).round().astype(np.uint8), 'RGBA')


def place(cut, cid):
    a = np.asarray(cut)[..., 3]
    ys, xs = np.nonzero(a > 8)
    box = cut.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    h = HEIGHT[cid]; w = round(box.width * h / box.height)
    assert w <= W, f'{cid} 縮完太寬 {w}'
    fig = resize_premul(box, w, h)
    canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    canvas.alpha_composite(fig, ((W - w) // 2, H - FOOT - h))
    return canvas


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        for raw in sorted((CHAR / 'raw').glob('*.png')):
            cid = raw.stem.split('-')[0]
            k = pathlib.Path(tmp) / 'k.png'
            key = KEYS.get(cid, KEY)
            subprocess.run([sys.executable, str(CUT), 'key', str(raw), '--key', key, '-o', str(k)], check=True, capture_output=True)
            out = pathlib.Path(tmp) / 'p.png'
            place(Image.open(k).convert('RGBA'), cid).save(out)
            subprocess.run([sys.executable, str(CUT), 'despill', str(out), '--key', key, '-o', str(out)], check=True, capture_output=True)
            Image.open(out).save(CHAR / f'{raw.stem}.webp', quality=90, method=6)
            print('wrote', raw.stem, flush=True)
