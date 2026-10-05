"""產 assets/placeholder/ 的純色佔位圖，正式美術到位前讓建置跑得動。python3 src/placeholders.py"""
import pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets/placeholder'
SPECS = {'bg.png': ('1920x1080', '#cfe8f3'), 'cg.png': ('1920x1080', '#f2c14e'), 'vocab.png': ('512x512', '#c9e4b4')}

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (size, color) in SPECS.items():
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', f'color=c={color}:s={size}',
                        '-frames:v', '1', str(OUT / name)], check=True)
    print('wrote', OUT)
