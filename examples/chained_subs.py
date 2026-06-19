from pathlib import Path
from sub2clip.sub2clip import extract_subs
from returns.result import Success, Failure

video = Path('input.mkv')
subs = extract_subs(video).unwrap()

sub = subs[10]
print(sub.prv)
print(sub)
print(sub.nxt)
