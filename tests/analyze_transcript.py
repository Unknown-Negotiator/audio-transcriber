"""Descriptive output diagnostics, not speech-recognition accuracy scoring."""
import json,re,sys
from pathlib import Path
p=Path(sys.argv[1]); duration=float(sys.argv[2])
rows=[]
for line in p.read_text().splitlines():
 m=re.match(r'\[([\d.]+)–([\d.]+)\] (.*)',line)
 if m: rows.append((float(m[1]),float(m[2]),m[3]))
text=' '.join(r[2] for r in rows)
gaps=[{'after_seconds':a[1],'before_seconds':b[0],'gap_seconds':b[0]-a[1]}
      for a,b in zip(rows,rows[1:]) if b[0]-a[1]>10]
result={'segment_count':len(rows),'word_count':len(text.split()),'media_duration_seconds':duration,
'first_segment_start':rows[0][0] if rows else None,'last_segment_end':rows[-1][1] if rows else None,
'unrepresented_tail_seconds':duration-rows[-1][1] if rows else None,
'gaps_over_10_seconds':gaps,'time_order_monotonic':all(b[0]>=a[0] for a,b in zip(rows,rows[1:])),
'cyrillic_character_count':len(re.findall(r'[А-Яа-яЁё]',text)),
'note':'Timestamps and script counts indicate processing extent, not word-level completeness or accuracy.'}
print(json.dumps(result,ensure_ascii=False,indent=2))
