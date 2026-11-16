#!/usr/bin/env bash
# 发布到 GitHub Pages。
#
# 用法：
#   ./deploy.sh                              # 只提交，不推
#   ./deploy.sh git@github.com:me/pinyin.git # 推到这个仓库
#
# 前提（二选一）：
#   A. 装了 gh 并已 `gh auth login`（推荐，脚本会自动建仓库 + 开 Pages）
#   B. 在 GitHub 网页上先建好空仓库，把地址传给本脚本
set -euo pipefail
cd "$(dirname "$0")"

REMOTE="${1:-}"
BRANCH="main"

# 1. 内容一致性检查：缺卡/缺音直接拦下，别把残页发上网
python3 - <<'PY'
import json, os, sys
d = json.load(open("data/curriculum.json", encoding="utf-8"))
miss = []
for lv in d["levels"]:
    for g in lv["groups"]:
        for it in g["items"]:
            i = it["id"]
            for p in (f"assets/cards/web/{i:03d}_card.webp",
                      f"assets/audio/{i:03d}_hz.mp3"):
                if not os.path.exists(p):
                    miss.append(p)
if miss:
    print(f"❌ 有 {len(miss)} 个资源缺失，先跑 build/run_all.py 或 build/optimize_images.py")
    for p in miss[:8]:
        print("   ", p)
    sys.exit(1)
print("✅ 资源齐全")
PY

# 2. 提交
if [ ! -d .git ]; then
  git init -q -b "$BRANCH"
fi
git add -A
if git diff --cached --quiet; then
  echo "没有改动，跳过提交"
else
  git commit -q -m "chore: 更新拼音卡片站 $(date '+%Y-%m-%d %H:%M')"
  echo "✅ 已提交"
fi

# 3. 推送 / 建仓
if [ -n "$REMOTE" ]; then
  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$REMOTE"
  else
    git remote add origin "$REMOTE"
  fi
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "⏭  没有配置远程仓库，只做了本地提交。"
  echo "   下次带上地址再跑：./deploy.sh git@github.com:<你>/<仓库>.git"
  exit 0
fi

git push -u origin "$BRANCH"
echo "✅ 已推送"

# 4. 有 gh 就顺手把 Pages 打开
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
  gh api -X POST "repos/$REPO/pages" -f "source[branch]=$BRANCH" -f "source[path]=/" >/dev/null 2>&1 \
    || gh api -X PUT "repos/$REPO/pages" -f "source[branch]=$BRANCH" -f "source[path]=/" >/dev/null 2>&1 \
    || true
  OWNER="${REPO%%/*}"; NAME="${REPO##*/}"
  echo "🌍 地址（首次生效要等 1~2 分钟）: https://${OWNER,,}.github.io/${NAME}/"
else
  echo "ℹ️  没装 gh：去仓库 Settings → Pages → Source 选「Deploy from a branch」→ main /(root)"
fi
