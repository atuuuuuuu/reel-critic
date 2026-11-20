#!/usr/bin/env bash
# Re-render only the shots that cover the given times, then re-concat and re-master (no full render).
#   rerender.sh <reel-folder> <t1,t2,...>      e.g. rerender.sh ~/reels/metro 1.0,45.2,50.5
# Needs a previous full build (seg/shot_NN.mp4 for every shot). Uses the stickman3d engine's render.js and make.sh.
set -euo pipefail
DIR="$(cd "${1:?usage: rerender.sh <reel> <times>}" && pwd)"; TIMES="${2:?times}"
ENGINE="${STICK_ENGINE:-$HOME/.claude/skills/stickman3d/engine}"
KIT="${STICK_KIT:-$HOME/.claude/plugins/cache/claude-animation-skills/animation-skills/1.0.0/kit}"
export NODE_PATH="$KIT/node_modules" CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
cd "$DIR"
# map times to shot ids from the page's own shot spans
IDS=$(node -e '
const { chromium } = require("playwright");
(async () => { const b = await chromium.launch({ executablePath: process.env.CHROME, args: ["--allow-file-access-from-files", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
  const p = await b.newPage(); await p.goto("file://" + process.cwd() + "/web/index.html"); await p.waitForFunction(() => window.SHOT_SPANS || window.LOAD_ERR, null, { timeout: 60000 });
  const sp = await p.evaluate(() => window.SHOT_SPANS); await b.close();
  const ids = new Set(process.argv[1].split(",").map(Number).map(t => sp.findIndex(([s, e]) => t >= s && t < e)).filter(i => i >= 0));
  console.log([...ids].sort((a, b) => a - b).join(","));
})();' "$TIMES")
[ -n "$IDS" ] || { echo "no shot covers $TIMES"; exit 1; }
echo "== re-rendering shots $IDS"
WORKERS="${WORKERS:-4}"; pids=(); IFS=, read -ra ALL <<< "$IDS"
for ((w = 0; w < WORKERS; w++)); do
  ids=""; for ((i = w; i < ${#ALL[@]}; i += WORKERS)); do ids="${ids:+$ids,}${ALL[$i]}"; done
  [ -n "$ids" ] && { node "$ENGINE/tools/render.js" segments "$ids" > "seg/relog$w.txt" 2>&1 & pids+=($!); }
done
for p in "${pids[@]}"; do wait "$p"; done
for f in seg/shot_??.mp4; do echo "file '$PWD/$f'"; done > seg/list.txt
ffmpeg -v error -y -f concat -safe 0 -i seg/list.txt -c copy silent.mp4
AUDIO_ONLY=1 bash "$ENGINE/make.sh" "$DIR" keep | tail -3
