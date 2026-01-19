from pathlib import Path
from sub2clip.sub2clip import generate
from sub2clip.generation import ClipSettings, VideoFormat, TextStyle
from sub2clip.subtitles import Subtitle

video = Path('office.mp4')

# Example: use a single subtitle timing to build a clip
sub1 = Subtitle(start=0, end=2000, text=['NO GOD'], delay=300)
sub2 = Subtitle(start=3200, end=7000, text=['No God, please no.', 'No. No.'])
sub3 = Subtitle(start=8200, end=11000, text=['NOOOOOOOOOO'])

text_style = TextStyle(
    font_size=50,
    bold=1,
    font="Google Sans"
)

clip_settings = ClipSettings(
	input_path=video,
	clip_path=Path('output/clip.mp4'),
	output_path=Path('output/clip.gif'),
	output_format=VideoFormat.GIF,
    hd_gif=True,
	start=sub1.start,
	end=sub3.end,
	fps=20,
	resolution=400,
    crop=True,
    subtitle_style=text_style
)

err, ok = generate(clip_settings, subtitles=[sub1, sub2, sub3])
if not ok:
	raise RuntimeError(err)

print('Generated:', clip_settings.output_path)
