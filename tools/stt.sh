#!/usr/bin/env bash
# Transcribe the finished reel with ElevenLabs Scribe through Composio -> <reel>/audio/stt_final.json
#   stt.sh <reel-folder> [video.mp4] [lang]      lang: mon (default), eng, ...
# If the Composio ElevenLabs quota is empty, transcribe in the ElevenLabs web app (Speech to Text, export JSON
# with timestamps) and save the file as <reel>/audio/stt_final.json; critic.py reads any audio/stt*.json.
set -euo pipefail
DIR="$(cd "${1:?usage: stt.sh <reel> [video] [lang]}" && pwd)"; VID="${2:-$DIR/$(basename "$DIR").mp4}"; LANG_="${3:-mon}"
TMP="$DIR/audio/final_voice.mp3"; ffmpeg -v error -y -i "$VID" -vn -ac 1 -ar 22050 -b:a 64k "$TMP"
composio execute ELEVENLABS_TRANSCRIBE_AUDIO --file "$TMP" -d "{\"model_id\":\"scribe_v1\",\"language_code\":\"$LANG_\",\"tag_audio_events\":true}" > "$DIR/audio/stt_final.json"
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));t=d.get('data',d);t=t.get('data',t);print(t.get('text') or d.get('error'))" "$DIR/audio/stt_final.json"
