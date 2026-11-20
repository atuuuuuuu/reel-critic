#!/usr/bin/env python3
"""Measurable checks on a finished 9:16 reel -> <reel>/critic/report.json + report.md + contact sheets.

usage: critic.py <reel-folder> [video.mp4] [--stt stt.json] [--rules rules.json]
The picture review (faces, framing, signs, caption band) is done by Claude from the contact sheets;
this script measures what can be measured and says which build step to redo for each failure.
"""
import json, os, re, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:]]
opt = lambda k: args[args.index(k) + 1] if k in args else None
pos = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or not args[i - 1].startswith('--'))]
REEL = os.path.abspath(pos[0])
VIDEO = os.path.abspath(pos[1]) if len(pos) > 1 else os.path.join(REEL, os.path.basename(REEL) + '.mp4')
RULES = json.load(open(opt('--rules') or os.path.join(HERE, '..', 'rules.json')))
OUT = os.path.join(REEL, 'critic'); os.makedirs(OUT, exist_ok=True)
checks = []


def check(name, ok, value, want, fix, note=''):
    checks.append({'check': name, 'pass': bool(ok), 'value': value, 'want': want, 'fix': fix, 'note': note})


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


# ---------- file ----------
p = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', VIDEO]).stdout)
v = next(s for s in p['streams'] if s['codec_type'] == 'video')
a = next((s for s in p['streams'] if s['codec_type'] == 'audio'), None)
dur = float(p['format']['duration']); fps = eval(v['r_frame_rate'])
R = RULES
check('length', R['length_s'][0] <= dur <= R['length_s'][1], round(dur, 2), f"{R['length_s'][0]}-{R['length_s'][1]} s", 'script')
check('size', (int(v['width']), int(v['height'])) == (1080, 1920), f"{v['width']}x{v['height']}", '1080x1920', 'render')
check('fps', abs(fps - 30) < .01, round(fps, 2), '30', 'render')
check('codecs', v['codec_name'] == 'h264' and a is not None and a['codec_name'] == 'aac', f"{v['codec_name']}/{a and a['codec_name']}", 'h264/aac', 'master')
check('file size', os.path.getsize(VIDEO) < R['max_mb'] * 1e6, f"{os.path.getsize(VIDEO) / 1e6:.0f} MB", f"< {R['max_mb']} MB", 'master',
      'TikTok/Instagram re-encode anyway; big files upload slowly on mobile data')

# ---------- loudness ----------
lo = run(['ffmpeg', '-hide_banner', '-i', VIDEO, '-af', 'ebur128=peak=true', '-f', 'null', '-']).stderr
I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', lo)[-1]); TP = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', lo)[-1])
check('loudness', R['lufs'][0] <= I <= R['lufs'][1], I, f"{R['lufs'][0]} to {R['lufs'][1]} LUFS", 'master', 'phones: -10 target')
check('true peak', TP <= R['max_tp'], TP, f"<= {R['max_tp']} dBTP", 'master')

# ---------- audio: voice start, gaps, voice over bed ----------
SR = 16000
pcm = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', VIDEO, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout, np.float32)
vo_path = os.path.join(REEL, 'audio', 'vo.wav')
if os.path.exists(vo_path):  # the dry voice tells speech from music/SFX exactly
    vo = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', vo_path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout, np.float32)
else:
    vo = pcm
hop = SR // 20
db = lambda x: 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-9)
vdb = np.array([db(vo[i:i + hop]) for i in range(0, len(vo) - hop, hop)])
speech = vdb > vdb.max() - 30
first = np.argmax(speech) / 20
check('voice starts', first <= R['voice_start_s'], round(first, 2), f"<= {R['voice_start_s']} s", 'voice', 'hook on frame 1')
gaps, run_len = [], 0
last_speech = len(speech) - np.argmax(speech[::-1])
for i, s in enumerate(speech[:last_speech]):
    if not s: run_len += 1
    else:
        if run_len / 20 > R['max_gap_s'] and i / 20 > first + .1: gaps.append([round((i - run_len) / 20, 2), round(run_len / 20, 2)])
        run_len = 0
check('voice gaps', not gaps, gaps or 'none', f"no silence > {R['max_gap_s']} s", 'voice', '[start, length] in seconds; trim the take or tighten line gaps')
if os.path.exists(vo_path):
    mdb = np.array([db(pcm[i:i + hop]) for i in range(0, min(len(pcm), len(vo)) - hop, hop)])
    n = min(len(mdb), len(speech))
    sp, gp = mdb[:n][speech[:n]], mdb[:n][~speech[:n]]
    gp = gp[gp > -70]  # ignore true silence
    ratio = round(float(np.median(sp) - np.median(gp)), 1) if len(gp) else 99
    check('voice over bed', ratio >= R['voice_over_bed_db'], ratio, f">= {R['voice_over_bed_db']} dB (speech vs pauses)", 'mix', 'music/SFX too loud if low')

# ---------- picture: hook motion and still stretches ----------
W, H, FR = 54, 96, 10
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', VIDEO, '-vf', f'fps={FR},scale={W}:{H},format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(float)
step = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))           # frame-to-frame motion
k = int(R['still_window_s'] * FR)
change = np.array([np.abs(fr[i] - fr[i - k]).mean() for i in range(k, len(fr))])  # how much the picture changed over the window
hook = float(step[:int(.5 * FR)].mean()) if len(step) else 0
check('hook motion', hook >= R['hook_motion'], round(hook, 2), f">= {R['hook_motion']} (motion in first 0.5 s)", 'camera', 'something must move on frame 1')
stills, i = [], 0
while i < len(change):
    if change[i] < R['still_change']:
        j = i
        while j < len(change) and change[j] < R['still_change']: j += 1
        stills.append([round((i) / FR, 1), round((j - i) / FR + R['still_window_s'], 1)]); i = j
    else: i += 1
check('picture keeps changing', not stills, stills or 'none', f"no stretch > {R['still_window_s']} s that barely changes", 'camera', '[start, length]: add a glide, push or new subject')
# a cut is one big jump with calm frames on both sides; a whip glide moves over several frames
cuts = sum(1 for i in range(1, len(step) - 1) if step[i] > R['cut_step'] and step[i - 1] < R['cut_step'] / 3 and step[i + 1] < R['cut_step'] / 3)
check('hard cuts', cuts <= R['max_hard_cuts'], cuts, f"<= {R['max_hard_cuts']}", 'camera', 'style: one continuous camera')

# ---------- words: transcript vs script ----------
def load_stt(f):  # ElevenLabs Scribe json (API via Composio, or web-app export); None if it holds an error
    try: d = json.load(open(f)); d = d.get('data', d); d = d.get('data', d)
    except Exception: return None
    return d if isinstance(d, dict) and ('text' in d or 'segments' in d) else None
adir = os.path.join(REEL, 'audio')
cands = [opt('--stt')] if opt('--stt') else sorted((os.path.join(adir, f) for f in os.listdir(adir) if f.startswith('stt') and f.endswith('.json')),
                                                    key=lambda f: 'stt_final' not in f) if os.path.isdir(adir) else []
d = next((x for x in map(load_stt, cands) if x), None)
norm = lambda s: re.sub(r'[^\w]', '', s.lower())
if d and os.path.exists(os.path.join(REEL, 'script.json')):
    heard = d['text'] if 'text' in d else ' '.join(s['text'] for s in d['segments'])
    heard = re.sub(r'\[[^\]]*\]', ' ', heard)
    script = ' '.join(re.sub(r'\[[^\]]*\]', ' ', l) for l in json.load(open(os.path.join(REEL, 'script.json'))))
    swaps = json.load(open(os.path.join(REEL, 'captions.json'))) if os.path.exists(os.path.join(REEL, 'captions.json')) else {}
    for src, dst in sorted(swaps.items(), key=lambda kv: -len(kv[0])): script = re.sub(re.escape(src), dst, script, flags=re.I)  # STT writes digits
    A, B = [norm(x) for x in script.split() if norm(x)], [norm(x) for x in heard.split() if norm(x)]
    # word-level edit distance with the differing words listed
    D = np.zeros((len(A) + 1, len(B) + 1), int); D[:, 0] = range(len(A) + 1); D[0, :] = range(len(B) + 1)
    for x in range(1, len(A) + 1):
        for y in range(1, len(B) + 1): D[x, y] = min(D[x - 1, y] + 1, D[x, y - 1] + 1, D[x - 1, y - 1] + (A[x - 1] != B[y - 1]))
    diffs, x, y = [], len(A), len(B)
    while x or y:
        if x and y and D[x, y] == D[x - 1, y - 1] + (A[x - 1] != B[y - 1]):
            if A[x - 1] != B[y - 1]: diffs.append(f"{A[x - 1]} -> {B[y - 1]}")
            x, y = x - 1, y - 1
        elif x and D[x, y] == D[x - 1, y] + 1: diffs.append(f"{A[x - 1]} -> (missing)"); x -= 1
        else: diffs.append(f"(extra) -> {B[y - 1]}"); y -= 1
    wer = D[-1, -1] / max(1, len(A))
    check('words match script', wer <= R['max_wer'], f"{wer:.1%}, {len(diffs[::-1])} diffs", f"<= {R['max_wer']:.0%}", 'voice',
          '; '.join(diffs[::-1][:12]) + ' (STT spelling slips are fine; mispronounced words are not: listen to these)')
else:
    check('words match script', False, 'no transcript', 'ElevenLabs STT json in audio/stt*.json', 'voice', 'run tools/stt.sh first')

# ---------- contact sheets for the picture review ----------
sheet_dir = os.path.join(OUT, 'sheets'); os.makedirs(sheet_dir, exist_ok=True)
safe = R['safe']; band = R['caption_band']
draw = (f"drawbox=x={safe[0]}:y={safe[1]}:w={safe[2] - safe[0]}:h={safe[3] - safe[1]}:color=cyan@0.8:t=6,"
        f"drawbox=x=0:y={band[0]}:w=1080:h={band[1] - band[0]}:color=yellow@0.25:t=fill")
n_sheets = int(np.ceil(dur / 10))
for s in range(n_sheets):  # frame i of sheet_NN is at NN*10 + i s; safe zone (cyan) + caption band (yellow) drawn on
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(s * 10), '-t', '10', '-i', VIDEO, '-vf',
                    f"fps=1,{draw},scale=216:384,tile=10x1", '-frames:v', '1', os.path.join(sheet_dir, f'sheet_{s:02d}.jpg')])

passed = all(c['pass'] for c in checks)
rep = {'video': VIDEO, 'duration': round(dur, 2), 'measured_pass': passed, 'checks': checks,
       'sheets': sorted(os.path.join(sheet_dir, f) for f in os.listdir(sheet_dir)), 'picture_review': 'pending (Claude fills this in)'}
json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), ensure_ascii=False, indent=1)
lines = [f"# Critic: {os.path.basename(VIDEO)} ({dur:.1f} s)", '', '| check | result | value | want | redo |', '|---|---|---|---|---|']
for c in checks: lines.append(f"| {c['check']} | {'PASS' if c['pass'] else 'FAIL'} | {c['value']} | {c['want']} | {'' if c['pass'] else c['fix']} |")
lines += [''] + [f"- {c['check']}: {c['note']}" for c in checks if not c['pass'] and c['note']]
open(os.path.join(OUT, 'report.md'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines)); print('\nsheets:', sheet_dir)
sys.exit(0 if passed else 1)
