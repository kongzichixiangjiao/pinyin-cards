# -*- coding: utf-8 -*-
"""把真人录音导进来，替换对应卡片的发音。

用法：
  python3 build/import_recordings.py                  # 读 录音/ 目录
  python3 build/import_recordings.py --src ~/Desktop/录音
  python3 build/import_recordings.py --dry-run        # 只看会处理哪些，不写文件

文件名规则：{编号}.m4a / .mp3 / .wav / .aac / .caf，例如 007.m4a、014.mp3
  也接受 007_b.m4a 这种带后缀的写法。

处理：
  切首尾静音 → 峰值归一到 -3dB（线性增益，不改音色）→ 24kHz / 单声道 / 96kbps
  → 写到 data/audio_override/{编号}.mp3

然后跑：
  cd build && python3 build_audio.py      # 套用到 assets/audio/
  python3 build_video.py all              # 重出视频
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DEFAULT = os.path.join(ROOT, "录音")
DST = os.path.join(ROOT, "data", "audio_override")
SYL = os.path.join(ROOT, "data", "audio_syllable")   # L2 的音节，交给 build_blend_audio 去拼
EXTS = (".m4a", ".mp3", ".wav", ".aac", ".caf", ".flac", ".aiff")

TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,"
        "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,"
        "areverse")


def peak_db(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "volumedetect",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.search(r"max_volume: (-?[\d.]+) dB", out)
    return float(m.group(1)) if m else -3.0


def convert(src, dst):
    """切静音 + 峰值归一 + 24k 单声道 96k mp3"""
    gain = max(-15.0, min(-3.0 - peak_db(src), 15.0))
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", src,
        "-af", f"{TRIM},volume={gain:.1f}dB",
        "-ac", "1", "-ar", "24000", "-b:a", "96k",
        "-write_xing", "0", dst,
    ], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=SRC_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.load(open(os.path.join(ROOT, "data", "curriculum.json"), encoding="utf-8"))
    known = {it["id"]: it for lv in data["levels"]
             for g in lv["groups"] for it in g["items"]}

    if not os.path.isdir(args.src):
        sys.exit(f"没找到录音目录：{args.src}\n先建一个，把 007.m4a 这种丢进去。")

    files = {}
    for f in sorted(os.listdir(args.src)):
        stem, ext = os.path.splitext(f)
        if ext.lower() not in EXTS:
            continue
        m = re.match(r"^(\d{1,3})(?:[_\-\s].*)?$", stem)
        if not m:
            print(f"  ? 跳过（文件名要像 007.m4a）：{f}")
            continue
        i = int(m.group(1))
        if i not in known:
            print(f"  ? 跳过（没有编号 {i} 的卡片）：{f}")
            continue
        files[i] = os.path.join(args.src, f)

    if not files:
        sys.exit("没找到可用的录音文件。")

    os.makedirs(DST, exist_ok=True)
    os.makedirs(SYL, exist_ok=True)
    done = []
    for i, src in sorted(files.items()):
        it = known[i]
        # L2 拼读卡：录的是「音节」，存到 audio_syllable，由 build_blend_audio 拼成 l…a…là
        dst = os.path.join(SYL if it.get("blend") else DST, f"{i:03d}.mp3")
        if args.dry_run:
            print(f"  [dry] {i:03d} <- {os.path.basename(src)}  （{it['text']}）")
            continue
        convert(src, dst)
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", dst], capture_output=True, text=True).stdout.strip()
        done.append(i)
        print(f"  ✓ {i:03d} {it['text']:<5} {os.path.basename(src):<24} {float(dur):.2f}s")

    if args.dry_run:
        return

    print(f"\n导入 {len(done)} 条 -> data/audio_override/")

    # 缺哪些（只统计 L1，L2 可选）
    l1_ids = [it["id"] for lv in data["levels"] if lv["code"] == "L1"
              for g in lv["groups"] for it in g["items"]]
    miss = [i for i in l1_ids if i not in done and not os.path.exists(
        os.path.join(DST, f"{i:03d}.mp3"))]
    if miss:
        print(f"L1 还缺 {len(miss)} 条：" + ", ".join(f"{i:03d}" for i in miss[:20])
              + (" …" if len(miss) > 20 else ""))
    else:
        print("L1 67 条齐了。")

    print("\n下一步：\n  cd build && python3 build_audio.py\n  python3 build_video.py all")


if __name__ == "__main__":
    main()
