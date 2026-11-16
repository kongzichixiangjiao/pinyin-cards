# -*- coding: utf-8 -*-
"""L2 拼读卡重新配「拼读音」：把「l — à → là」真的读成 l … a … là

问题：原来 say 填的是例词（蜡烛），TTS 直接读"蜡烛"，没读拼音拼读过程。
现在合成三段：
  ① 声母（用 L1 的教材范读，如 l）
  ② 介母 / 韵母（用 L1 范读，如 a / i / u）
  ③ 音节（用例词里对应那个字做 TTS，如"蜡" → là，带正确声调）

输出到 data/audio_override/{id}.mp3，build_audio.py 会自动套用。

用法： python3 build/build_blend_audio.py [--force]
"""
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata

import edge_tts
from pypinyin import Style, lazy_pinyin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "curriculum.json")
AUDIO = os.path.join(ROOT, "assets", "audio")
OVERRIDE = os.path.join(ROOT, "data", "audio_override")

VOICE = "zh-CN-XiaoyiNeural"
RATE = "-18%"          # 放慢一点，孩子跟得上
GAP = 0.35


def strip_tone(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.replace("ü", "ü").strip().lower()


def dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.5


async def tts(text, path):
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(path)
    # 剪掉首尾静音 + 统一 24k/96k
    tmp = path + ".t.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,"
                    "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse",
                    "-ac", "1", "-ar", "24000", "-b:a", "96k", tmp], check=True)
    os.replace(tmp, path)


def silence(sec, path):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=24000:cl=mono", "-t", str(sec), path], check=True)


def concat(paths, out):
    """先统一转成 wav 再拼 —— 直接拼 mp3 会撞上 libmp3lame 的帧填充 bug"""
    d = tempfile.mkdtemp()
    wavs = []
    for i, p in enumerate(paths):
        w = os.path.join(d, "c%02d.wav" % i)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", p,
                        "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", w], check=True)
        wavs.append(w)
    lst = os.path.join(d, "list.txt")
    with open(lst, "w") as f:
        for w in wavs:
            f.write(f"file '{w}'\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c:a", "libmp3lame", "-b:a", "96k", "-ar", "24000",
                    "-ac", "1", out], check=True)


# 个别字 pypinyin 给的是另一读法，人工指定
FALLBACK_CHAR = {"fó": "佛"}


def find_char_for(text, syllable):
    """在例词里找出读音等于目标音节的那个字"""
    if syllable.lower() in FALLBACK_CHAR:
        return FALLBACK_CHAR[syllable.lower()]
    for ch in text:
        py = lazy_pinyin(ch, style=Style.TONE, errors="ignore")
        if py and py[0].lower() == syllable.lower():
            return ch
    return None


def main():
    force = "--force" in sys.argv
    data = json.load(open(DATA, encoding="utf-8"))
    l1 = {}
    for lv in data["levels"]:
        if lv["code"] != "L1":
            continue
        for g in lv["groups"]:
            for it in g["items"]:
                l1[it["text"]] = it["id"]

    os.makedirs(OVERRIDE, exist_ok=True)
    tmpdir = tempfile.mkdtemp()
    sil = os.path.join(tmpdir, "sil.mp3")
    silence(GAP, sil)
    lead = os.path.join(tmpdir, "lead.mp3")
    silence(0.12, lead)

    todo = []
    for lv in data["levels"]:
        if lv["code"] != "L2":
            continue
        for g in lv["groups"]:
            for it in g["items"]:
                blend = it.get("blend", "")
                if "→" not in blend:
                    continue
                left, syl = blend.split("→")
                parts = [p.strip() for p in left.split("—") if p.strip()]
                if not parts:
                    continue
                todo.append((it, parts, syl.strip()))

    print(f"要合成 {len(todo)} 条拼读音")

    async def run():
        ok = 0
        for it, parts, syl in todo:
            out = os.path.join(OVERRIDE, f"{it['id']:03d}.mp3")
            if os.path.exists(out) and not force:
                continue
            clips = [lead]
            miss = []
            # 声母 / 介母 / 韵母，全部读出来，都用 L1 现成音频（教材范读）
            for p in parts:
                key = strip_tone(p)
                key = key.replace("v", "ü")
                if key in l1:
                    clips.append(os.path.join(AUDIO, "%03d_hz.mp3" % l1[key]))
                    clips.append(sil)
                else:
                    miss.append(key)
            # 最后一段：音节，用品词里那个字做 TTS
            ch = find_char_for(it["text"], syl)
            if ch:
                seg = os.path.join(tmpdir, f"s{it['id']}.mp3")
                await tts(ch, seg)
                clips.append(seg)
            else:
                miss.append(syl)
            if miss:
                print(f"  ! {it['id']} {it['text']}: 缺 {miss}，跳过")
                continue
            try:
                concat(clips, out)
            except subprocess.CalledProcessError:
                print(f"  ! {it['id']} {it['text']}: 拼接失败，跳过")
                continue
            ok += 1
            if ok % 10 == 0:
                print(f"  ... {ok}")
        print(f"完成 {ok} 条 -> data/audio_override/")

    asyncio.run(run())


if __name__ == "__main__":
    main()
