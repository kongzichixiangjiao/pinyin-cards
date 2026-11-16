# -*- coding: utf-8 -*-
"""一键重建：卡片图 -> 小纸条 -> 配音 -> 视频 -> index.html"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("卡片图 + 小纸条", ["build_cards.py"]),
    ("读音配音 (edge-tts)", ["build_audio.py"]),
    ("视频合成 (ffmpeg)", ["build_video.py"]),
    ("交互页 index.html", ["build_index.py"]),
]

if __name__ == "__main__":
    t0 = time.time()
    for i, (name, args) in enumerate(STEPS, 1):
        print(f"\n[{i}/{len(STEPS)}] {name} ...", flush=True)
        r = subprocess.run([sys.executable] + args, cwd=HERE)
        if r.returncode != 0:
            sys.exit(f"× 失败：{name}")
    print(f"\n全部完成，用时 {time.time()-t0:.0f} 秒")
