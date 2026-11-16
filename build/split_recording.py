# -*- coding: utf-8 -*-
"""把「一口气念完」的长录音自动切成一条一条。

为什么要有这个：67 个音在手机上一个个改文件名太受罪。
更好的办法是——按清单顺序连着念，每个音之间停 1 秒左右，剩下的我自动切。

用法：
  python3 build/split_recording.py 录音/整段.m4a             # 默认按 L1 67 条切
  python3 build/split_recording.py 录音/整段.m4a --count 67
  python3 build/split_recording.py 录音/整段.m4a --start 1    # 从第几条开始对应
  python3 build/split_recording.py 录音/整段.m4a --dry-run    # 只看能切出几段

切出来的文件写进 录音/ 目录，命名 001.mp3、002.mp3……，然后跑 import_recordings.py
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def probe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return float(out)


def detect_silences(path, noise="-38dB", min_sil=0.45):
    """返回 [(start, end), ...] 静音区间"""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af",
                          f"silencedetect=noise={noise}:d={min_sil}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(m) for m in re.findall(r"silence_start: (-?[\d.]+)", out)]
    ends = [float(m) for m in re.findall(r"silence_end: (-?[\d.]+)", out)]
    return list(zip(starts, ends + [None] * (len(starts) - len(ends))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--count", type=int, default=67)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(ROOT, "录音"))
    ap.add_argument("--noise", default="-38dB")
    ap.add_argument("--min-sil", type=float, default=0.45)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.audio):
        sys.exit(f"找不到文件：{args.audio}")

    total = probe_duration(args.audio)
    sils = detect_silences(args.audio, args.noise, args.min_sil)

    # 用静音区间的中点做切点；开头结尾各补一刀
    cuts = [0.0]
    for s, e in sils:
        if e is None:
            continue
        mid = (s + e) / 2
        if 0.15 < mid < total - 0.15:
            cuts.append(mid)
    cuts.append(total)

    segs = [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)]
    segs = [(a, b) for a, b in segs if b - a > 0.12]

    # 去掉纯静音的段（开头/结尾的空白）
    kept = []
    for a, b in segs:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
                              "-i", args.audio, "-af", "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        m = re.search(r"mean_volume: (-?[\d.]+) dB", out)
        if m and float(m.group(1)) > -45:
            kept.append((a, b))
    segs = kept

    print(f"文件时长 {total:.1f}s，检测到 {len(sils)} 处停顿，切出 {len(segs)} 段")
    if len(segs) != args.count:
        print(f"⚠️  段数 {len(segs)} ≠ 预期 {args.count}")
        print("   常见原因：某个音之间停得太短（<0.45s）被连在一起，或者中间咳嗽/翻页被切开。")
        print("   可以先 --dry-run 看段数，调 --min-sil 到 0.6~0.8 再试。")
    if args.dry_run:
        for i, (a, b) in enumerate(segs, 1):
            print(f"  {i:>3}  {a:6.2f}s - {b:6.2f}s  ({b-a:.2f}s)")
        return

    os.makedirs(args.out, exist_ok=True)
    n = 0
    for i, (a, b) in enumerate(segs):
        idx = args.start + i
        if idx > args.count:
            break
        dst = os.path.join(args.out, f"{idx:03d}.mp3")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
                        "-i", args.audio, "-ac", "1", "-ar", "24000", "-b:a", "96k", dst],
                       check=True)
        n += 1

    print(f"写出 {n} 个文件 -> {args.out}/")
    print("下一步： python3 build/import_recordings.py")


if __name__ == "__main__":
    main()
