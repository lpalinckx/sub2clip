from pathlib import Path
from sub2clip.sub2clip import extract_subs

video = Path('input.mkv')
subs, ok = extract_subs(video)
if not ok:
	raise RuntimeError(subs)

sub = subs[10]
print(sub.prv) 
print(sub)
print(sub.nxt) 
