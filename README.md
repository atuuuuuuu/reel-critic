# reel-critic

A Claude Code skill that reviews a finished 9:16 reel before it is posted and sends it back until it passes.
It was built for the `/stickman3d` engine (code-animated stick-figure shorts) but the checks work on any vertical mp4.

- `tools/critic.py`: measured checks (format, loudness, voice timing, voice over music, hook motion, still stretches, hard cuts, words vs script) and contact sheets with the safe zone and caption band drawn on.
- `tools/stt.sh`: ElevenLabs Scribe transcript of the final file through Composio.
- `tools/rerender.sh`: re-renders only the shots covering the given times, then re-masters (stickman3d engine).
- `tools/stats.py`: Instagram reel insights and TikTok video stats through Composio, to tune `rules.json` from real numbers.
- `rules.json`: every threshold in one place.
- `SKILL.md`: the review steps Claude follows, the picture checklist and the fix loop (only the failing step is redone, at most 3 rounds).

## Where the rules come from
Nothing here is an official platform number: TikTok, Instagram and YouTube publish no retention thresholds. The defaults are the stickman3d house format plus the points the public sources agree on, and the stats tool exists to replace them with the channel's own numbers.

- Hook: the first seconds decide distribution, and title cards or logos at the start cost retention. Sources: [Shortimize, watch time on TikTok vs Reels vs Shorts](https://www.shortimize.com/blog/compare-watch-time-tiktok-vs-reels-vs-shorts), [go-viral, the first 3 seconds](https://www.go-viral.app/blog/hook-first-3-seconds/), [Perceedigital, the 3-second rule](https://www.perceedigital.com/insights/video-hooks-that-convert/). Their percentages disagree with each other, so the critic checks timing (voice by 0.3 s, motion in 0.5 s), not a number of views.
- YouTube Shorts "viewed vs swiped away": community data puts 70 % or more as good, under 60 % as weak. Sources: [ReelRise](https://reelrise.app/guide/viewed-vs-swiped-away-the-only-youtube-shorts-metric-that-matters/), [1of10](https://1of10.com/blog/youtube-shorts-analytics/), [ContentMatch](https://contentmatch.io/youtube-shorts-algorithm-viewed-vs-swiped-ratio-2026/), [a study of 3.3 billion Shorts views](https://medium.com/@antoinelacombled/cracking-the-youtube-shorts-algorithm-a-study-of-3-3-billion-views-4711fdf7931b).
- Safe zones on 1080x1920: TikTok keeps about 320 px at the bottom and 120 px on the right for its UI, Reels about 310 px and 84 px; the tightest common zone is about 900x1400 centred. Sources: [AdaptlyPost](https://adaptlypost.com/en/blog/social-media-safe-zones-2026-complete-guide), [Remotion social safe zones](https://www.remotion.dev/elements/overlays/social-safe-zones/), [Ignite Social Media](https://www.ignitesocialmedia.com/content-creation/what-are-the-safe-zones-for-tiktoks-and-instagram-reels/).
- Loudness: -10 LUFS / -2 dBTP master, because YouTube only turns loud uploads down and Instagram and TikTok play files as uploaded (from the stickman3d engine notes).

## Other automation that was looked at
- Review gates in faceless-video tools: [AutoShorts.ai](https://autoshorts.ai/) and [Faceless.so](https://faceless.so/) let you approve each video before it posts; posting "private" or "only me" first to preview the platform UI is common advice.
- LLM-as-judge in n8n pipelines: a generator agent followed by a judge with a strict rubric and structured output ([automation exercise](https://louischancly.github.io/automation-exercise/exercises/03-llm-as-judge/part-b-workflow)); human review before upload ([n8n workflow 10644](https://n8n.io/workflows/10644-create-and-auto-publish-youtube-content-with-gemini-ai-face-thumbnails-and-human-review/)).
- Claude Code skills for posting: [sergebulaev/tiktok-skills](https://github.com/sergebulaev/tiktok-skills), [sergebulaev/instagram-skills](https://github.com/sergebulaev/instagram-skills), [cross-post to TikTok, Reels and Shorts](https://dev.to/fheijdenrijk/cross-post-video-to-tiktok-reels-and-shorts-with-claude-code-check-the-file-write-three-texts-b30). None of them reviews the video itself; that gap is why this skill exists.
- YouTube is adding its own pre-publish feedback for Shorts ([Search Engine Journal](https://www.searchenginejournal.com/youtube-gives-you-feedback-on-shorts-before-publishing/589088/)).

## Requirements
ffmpeg, Python 3 with numpy, the Composio CLI (ElevenLabs, Instagram, TikTok connections) and, for `rerender.sh`, the stickman3d engine with Playwright and Chrome.

## License
MIT

## Install
```bash
git clone https://github.com/<you>/reel-critic ~/.claude/skills/reel-critic
```
Then ask Claude Code to "review this reel" or run `/reel-critic` after a build.
