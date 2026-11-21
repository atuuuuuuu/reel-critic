# Critic: metro.mp4 (61.8 s)

| check | result | value | want | redo |
|---|---|---|---|---|
| length | PASS | 61.77 | 40-68 s |  |
| size | PASS | 1080x1920 | 1080x1920 |  |
| fps | PASS | 30.0 | 30 |  |
| codecs | PASS | h264/aac | h264/aac |  |
| file size | PASS | 206 MB | < 300 MB |  |
| loudness | PASS | -11.2 | -11.5 to -8.5 LUFS |  |
| true peak | PASS | -1.9 | <= -1.0 dBTP |  |
| voice starts | PASS | 0.1 | <= 0.3 s |  |
| voice gaps | PASS | none | no silence > 0.9 s |  |
| voice over bed | PASS | 10.9 | >= 9 dB (speech vs pauses) |  |
| hook motion | PASS | 5.61 | >= 1.0 (motion in first 0.5 s) |  |
| picture keeps changing | PASS | none | no stretch > 2.0 s that barely changes |  |
| hard cuts | PASS | 2 | <= 2 |  |
| words match script | PASS | 5.0%, 7 diffs | <= 8% |  |

