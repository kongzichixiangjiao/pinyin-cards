# -*- coding: utf-8 -*-
"""把普通话学习网（pthxx.com）的教材范读导入 data/audio_override/

源音：/tmp/pth/mp3/*.mp3（22.05kHz / 32kbps / 单声道，从 swf 里抽出来的）
目标：data/audio_override/{id}.mp3（24kHz / 96kbps / 单声道，和现有 TTS 完全一致，
      这样 build_video.py 的音频 concat 不会因为采样率不同出错）

build_audio.py 已经支持这个目录：跑完 TTS 后会把 override 复制过去，
--force 也不会冲掉。所以改完音频只要重跑 build_audio.py 即可。

用法： python3 build/import_fan_audio.py
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "/tmp/pth/mp3"
DST = os.path.join(ROOT, "data", "audio_override")

# 卡片上的字 -> 范读文件名（swf 名）
MAP = {
    # 声母 21（y / w 该栏目没做，保留现有 TTS）
    "b": "b", "p": "p", "m": "m", "f": "f", "d": "d", "t": "t", "n": "n",
    "l": "l", "g": "g", "k": "k", "h": "h", "j": "j", "q": "q", "x": "x",
    "zh": "zh", "ch": "ch", "sh": "sh", "r": "r", "z": "z", "c": "c", "s": "s",
    # 单韵母 6
    "a": "a", "o": "o", "e": "e", "i": "i", "u": "u", "ü": "v",
    # 复韵母 8
    "ai": "ai", "ei": "ei", "ui": "ui", "ao": "ao", "ou": "ou",
    "iu": "iu", "ie": "ie", "üe": "ve",
    # 鼻韵母 9
    "an": "an", "en": "en", "in": "in", "un": "un", "ün": "vn",
    "ang": "ang", "eng": "eng", "ing": "ing", "ong": "ong",
    # 整体认读 7（yi wu yu ye yue yuan yin yun ying 缺）
    "zhi": "zhi", "chi": "chi", "shi": "shi", "ri": "ri",
    "zi": "zi", "ci": "ci", "si": "si",
}


def convert(src, dst):
    """统一成 24kHz / 单声道 / 96kbps mp3，和现有 TTS 一致"""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", src,
        "-af", "loudnorm=I=-18:TP=-2:LRA=9",   # 短音也能用，这里只是为了和 TTS 音量齐
        "-ac", "1", "-ar", "24000", "-b:a", "96k", dst,
    ], check=True)


def main():
    data = json.load(open(os.path.join(ROOT, "data", "curriculum.json"), encoding="utf-8"))
    items = [it for lv in data["levels"] for g in lv["groups"] for it in g["items"]]

    os.makedirs(DST, exist_ok=True)
    done, missing = [], []
    for it in items:
        text = it["text"]
        if text not in MAP:
            continue
        src = os.path.join(SRC, MAP[text] + ".mp3")
        if not os.path.exists(src):
            missing.append(text)
            continue
        convert(src, os.path.join(DST, f"{it['id']}.mp3"))
        done.append(f"{it['id']:>3} {text}")

    print(f"导入 {len(done)} 条 -> data/audio_override/")
    print("  " + "  ".join(done))
    if missing:
        print("缺（保持 TTS）:", missing)
    print("\n下一步： cd build && python3 build_audio.py")


if __name__ == "__main__":
    main()
