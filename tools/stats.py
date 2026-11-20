#!/usr/bin/env python3
"""Pull the channel's real reel numbers through Composio and print what they say about the rules.

usage: stats.py [--out stats.json]
Instagram (business/creator account): views, reach, shares, saves, avg watch time per reel.
TikTok: views, likes, shares, duration per video.
Each platform is skipped with a note when its Composio connection is missing (`composio link instagram` / `composio link tiktok`).
"""
import json, subprocess, sys, statistics as st

out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else 'stats.json'


def comp(slug, data):
    r = subprocess.run(['composio', 'execute', slug, '-d', json.dumps(data)], capture_output=True, text=True, timeout=180)
    try: d = json.loads(r.stdout)
    except Exception: return None, (r.stdout or r.stderr)[:300]
    if not d.get('successful', True): return None, str(d.get('error'))[:300]
    d = d.get('data', d); return d.get('data', d), None


rows, notes = [], []
ig, err = comp('INSTAGRAM_GET_IG_USER_MEDIA', {'ig_user_id': 'me', 'limit': 50,
               'fields': 'id,caption,media_product_type,timestamp,permalink,insights.metric(views,reach,shares,saved,ig_reels_avg_watch_time)'})
if ig is None: notes.append(f'instagram skipped: {err}')
else:
    for m in (ig.get('data') if isinstance(ig, dict) else ig) or []:
        if m.get('media_product_type') != 'REELS': continue
        ins = {i['name']: (i.get('values') or [{}])[0].get('value') for i in (m.get('insights') or {}).get('data', [])}
        rows.append({'platform': 'instagram', 'id': m['id'], 'date': m.get('timestamp', '')[:10], 'title': (m.get('caption') or '')[:40].replace('\n', ' '),
                     'views': ins.get('views'), 'shares': ins.get('shares'), 'saves': ins.get('saved'),
                     'avg_watch_s': round((ins.get('ig_reels_avg_watch_time') or 0) / 1000, 1), 'duration_s': None, 'url': m.get('permalink')})
tt, err = comp('TIKTOK_LIST_VIDEOS', {'max_count': 20, 'fields': 'id,title,create_time,duration,view_count,like_count,share_count,share_url'})
if tt is None: notes.append(f'tiktok skipped: {err}')
else:
    for m in (tt.get('videos') if isinstance(tt, dict) else tt) or []:
        rows.append({'platform': 'tiktok', 'id': m.get('id'), 'date': str(m.get('create_time', '')), 'title': (m.get('title') or '')[:40],
                     'views': m.get('view_count'), 'shares': m.get('share_count'), 'saves': None, 'avg_watch_s': None,
                     'duration_s': m.get('duration'), 'url': m.get('share_url')})

json.dump({'rows': rows, 'notes': notes}, open(out, 'w'), ensure_ascii=False, indent=1)
for n in notes: print('note:', n)
if not rows: print('no posts found: connect an account, then rerun'); sys.exit(0)
rows.sort(key=lambda r: -(r['views'] or 0))
print(f"{'platform':10} {'date':10} {'views':>8} {'shares':>6} {'watch s':>7} {'len s':>5}  title")
for r in rows: print(f"{r['platform']:10} {r['date']:10} {r['views'] or 0:8} {r['shares'] or 0:6} {r['avg_watch_s'] or '':>7} {r['duration_s'] or '':>5}  {r['title']}")
# what the numbers suggest for rules.json: compare the top third with the rest
top = rows[:max(1, len(rows) // 3)]; rest = rows[len(top):]
for key in ('avg_watch_s', 'duration_s'):
    a = [r[key] for r in top if r[key]]; b = [r[key] for r in rest if r[key]]
    if a and b: print(f"top third {key}: median {st.median(a)} vs rest {st.median(b)}")
