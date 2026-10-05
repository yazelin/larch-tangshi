"""組出 dist/project.json：骨架＋劇本對話卡＋tangshi-kit 插件卡＋有條件連線。"""
import json, os, pathlib, shutil
ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT_ID = 'project-ac006859-4f72-4956-a83e-ddc2ed9a1c0a'


def load_skeleton():
    return json.loads((ROOT / 'skeleton/project.json').read_text())


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
