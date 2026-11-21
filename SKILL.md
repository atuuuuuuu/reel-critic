---
name: reel-critic
description: Reviews a finished 9:16 reel (TikTok, Instagram Reels, YouTube Shorts) before it is posted and sends it back for fixes until it passes. Measures length, format, loudness, voice timing, voice-over-music level, hook motion, still stretches and hard cuts, checks the spoken words against the script, then Claude reviews contact sheets for framing, caption-band and safe-zone problems. On a fail it redoes only the failing step (one shot, one voice line, the mix), up to 3 rounds. Ends with the caption and English hashtags. Use after every /stickman3d or /stickman3dmn build, or when the user asks to review, critique or QA a reel.
---

# /reel-critic

A reel is not finished until it passes. Run this after `make.sh` writes `<reel>/<name>.mp4`.
`PY` is any Python 3 with numpy (`PY=python3`; with the stickman engine, its kit Python works). `CRITIC="<base directory of this skill>"`.

## 1. Words
Transcribe the final mp4: `bash "$CRITIC/tools/stt.sh" <reel> [video] [mon|eng]` (ElevenLabs Scribe via Composio, writes `audio/stt_final.json`).
If the Composio ElevenLabs quota is empty, transcribe the mp4 in the ElevenLabs web app (Speech to Text, Export JSON with timestamps) and save it as `audio/stt_final.json`. Whisper is weak on Mongolian: do not use it for Mongolian reels.

## 2. Measure
`"$PY" "$CRITIC/tools/critic.py" <reel> [video.mp4]` writes `<reel>/critic/report.md`, `report.json` and `critic/sheets/sheet_NN.jpg` (one frame per second, 10 per sheet; frame i of sheet NN is at about NN*10 + i s). Exit code 0 means every measured check passed. Thresholds live in `rules.json`:

| check | rule | redo step |
|---|---|---|
| length | 40 to 68 s | script |
| size, fps, codecs | 1080x1920, 30 fps, h264 + aac | render / master |
| loudness, true peak | -11.5 to -8.5 LUFS, <= -1 dBTP | master |
| voice starts | first word by 0.3 s | voice |
| voice gaps | no silence over 0.9 s between lines | voice |
| voice over bed | speech at least 9 dB over the pauses (music + SFX) | mix |
| hook motion | something moves in the first 0.5 s | camera |
| picture keeps changing | no 2 s stretch where the frame barely changes | camera |
| hard cuts | at most 2 (whip glides are not cuts) | camera |
| words match script | word error rate <= 8 % after caption swaps | voice |

## 3. Look
Read every contact sheet (stack them: `ffmpeg -i sheet_00.jpg -i sheet_01.jpg ... -filter_complex vstack=N`). Cyan box: safe zone (x 100 to 980, y 220 to 1500). Yellow band: caption band (y 1250 to 1420). Fail the reel for:
- a face or the key prop of a beat under the caption band or outside the safe zone;
- the subject cut off by the frame edge, or a prop close to the lens covering the subject;
- a sign or title card with text the caption covers, or any English text on screen in a Mongolian reel;
- a beat whose picture does not show what the voice says at that moment (check the caption word on each frame);
- broken frames: black, missing textures, a character floating or sunk in the floor.
A frame in the middle of a whip glide may be blurred or show empty ground: that is fine. Write each finding with its time and the redo step in `report.md` under `## Picture`.

## 4. Verdict and fix loop
PASS only when step 2 exits 0, step 3 has no findings, and step 1's diff list has no word the voice actually got wrong (listen to the listed words; STT spelling slips do not count).
On FAIL, redo only what failed, then run steps 1 to 3 again. Stop after 3 rounds and show the user what still fails.
- camera / framing at a few times: edit `web/shots.js`, check with `render.js stills`, then `bash "$CRITIC/tools/rerender.sh" <reel> <t1,t2,...>` (re-renders only the shots covering those times, re-concats, re-masters). A change to a set seen in many shots needs the full `make.sh`.
- voice line: re-record that line (ElevenLabs, or your TTS), rebuild word times, rebuild the mix (`make.sh <reel> keep` with the stickman engine).
- mix / loudness: edit `audio.py`, `AUDIO_ONLY=1 make.sh <reel> keep`.
- script / length: back to the user; the script is theirs to approve.

## 5. Learn from real numbers
`python3 "$CRITIC/tools/stats.py" --out <reel>/critic/stats.json` pulls Instagram reel insights (views, shares, saves, average watch time) and TikTok video stats through Composio. It skips a platform that is not connected (`composio link instagram`, `composio link tiktok`; Instagram insights need a business or creator account). Once there are 10 or more posts, compare the top third with the rest (watch time, length, hook type) and propose `rules.json` changes to the user before making them.

## 6. Hand-over
Give the user: the mp4 path, length, measured loudness, the verdict table, picture findings fixed, and a caption for TikTok, Instagram and YouTube Shorts in the reel's language with 3 to 5 English hashtags (always `#whatif` for the Hervee channel, plus topic tags such as `#mongolia #ulaanbaatar`, `#fyp` on TikTok, `#shorts` on YouTube). The user posts by hand.

## Where the rules come from
See `README.md`: retention and hook research, safe-zone measurements and the automation tools that were looked at.
