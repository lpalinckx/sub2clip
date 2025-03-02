# Sub2Clip

## Requirements
[FFmpeg](https://ffmpeg.org/) installed on your system

## Installation
`pip install -r requirements.txt`

## Usage
- `python clip.py` opens the GUI.
- `python clip.py --video=/path/to/video` autoloads the given video.
- `python clip.py --directory=/path/to/directory` autoloads the given directory.

1. Load a video (or a directory of videos) that has a subtitles track
2. Search for a specific phrase or click on one of the shown subtitles
3. Adjust the various settings to your liking: FPS, subtitle string, resolution or font (size)
4. Click the 'Generate GIF' button, a preview will appear below after creating the gif
5. The created gif (and the original clip in .mp4) appears in the `./output/` directory

