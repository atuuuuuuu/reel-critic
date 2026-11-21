# Example: one reel, three rounds

A 62 s Mongolian "what if" short made with the stickman3d engine (three.js stick figures, ElevenLabs voice).

| round | what the critic caught | fix |
|---|---|---|
| 1 | narrator's face under the captions in the first 2 s; character above the safe zone at 40-44 s; a sign covered by captions at 50 s | camera framing + a prop moved; full re-render |
| 2 | a board cut off by the frame edge (3-10 s); 2.1 s where the picture barely changed (43 s); half a face peeking into the last shot | `rerender.sh` re-rendered 7 of 36 shots |
| 3 | 2.2 s still stretch after a stamp lands (7.7 s) | camera push-in; 2 shots re-rendered |
| final | all 14 measured checks pass, contact sheets clean | see `report-pass.md` |
