# Sub2Clip

## Usage

### Installation
Two packages exist in this project:
- sub2clip
- sub2clip-ui

`sub2clip-ui` is a GUI wrapper for the core package `sub2clip` created using PyQt5.

To only install the core package with the clip generation logic:
```bash
pip install -e packages/sub2clip
```

To run the user interface:
```bash
pip install -e packages/sub2clip-ui
sub2clip
```

### Extract subtitles from a video

```python
from pathlib import Path
from sub2clip.sub2clip import extract_subs

video = Path('input.mkv')
subs, ok = extract_subs(video)
if not ok:
	raise RuntimeError(subs)

# `subs` is a list of Subtitles — you can inspect entries like:
for sub in subs:
	print(sub.start, sub.end, sub.text)
```

### Generate a GIF/WEBP/MP4 clip using `ClipSettings`

```python
from pathlib import Path
from sub2clip.sub2clip import generate
from sub2clip.generation import ClipSettings, VideoFormat
from sub2clip.subtitles import Subtitle

video = Path('input.mp4')

# Example: use a single subtitle timing to build a clip
sub = Subtitle(start=10000, end=13000, text=['Hello world'], delay=0)

clip_settings = ClipSettings(
	input_path=video,
	clip_path=Path('output/clip.mp4'),
	output_path=Path('output/clip.webp'),
	output_format=VideoFormat.WEBP,
	start=sub.start,
	end=sub.end,
	fps=20,
	resolution=480,
)

err, ok = generate(clip_settings, subtitles=[sub])
if not ok:
	raise RuntimeError(err)

print('Generated:', clip_settings.output_path)
```

A larger example can be found at `examples/example.py`.

Notes:
- Use `VideoFormat.MP4` for MP4 output and set suitable `output_path` file extension.
- The library returns `(error_message, False)` on failure — `error_message` is a human-readable string.

## GUI Usage
- `sub2clip` opens the GUI.
- `sub2clip --video=/path/to/video` autoloads the given video.
- `sub2clip --directory=/path/to/directory` autoloads the given directory.

1. Load a video (or a directory of videos) that has a subtitle track
2. Search for a specific phrase or click on one of the shown subtitles
3. Adjust the various settings to your liking: FPS, subtitle string, resolution or font (size)
4. Click the 'Generate GIF' button, a preview will appear below after creating the gif
5. The created gif (and the original clip in .mp4) appears in the `./output` directory