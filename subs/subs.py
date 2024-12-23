import pysubs2
import tempfile
import os
from ffmpeg import (FFmpeg, FFmpegError)
from pathlib import Path

# Functions in this library return a second boolean value indicating success/failure
# In case of failure, the first return value is the error message

# Extract subs with ffmpeg to a tmp file (pysubs2 _only_ works with files).
# Load them with pysubs2 and return the result.
# The tmp dir is cleaned up automatically.
def extract_subs(video_path):
    with tempfile.TemporaryDirectory() as tmp:
        output_path = os.path.join(tmp, 'subs.srt')
        try:
            (
                FFmpeg()
                .option("y")
                .input(video_path)
                .output(
                    output_path,
                    map=["0:s:0"]
                )
            ).execute()
        except FFmpegError as e:
            return f'could not extract subtitles from video {video_path}: {e}', False

        if os.path.exists(output_path):
            return pysubs2.load(output_path), True
        else:
            return f'could not extract subtitles from video {video_path}', False

# Generate the chosen GIF with FFmpeg
def generate_gif(start_time, end_time, output_clip, output_gif, custom_text, video_path, fps, crop, resolution, font, font_size):
    if start_time >= end_time:
        return f'duration must be at least 1 second', False

    duration = end_time - start_time

    # Clip the video, needed because seeking to the right spot tends to break otherwise
    (
        FFmpeg()
        .option("y")
        .option("ss", value=start_time)
        .input(video_path)
        .option("t", value=duration)
        .output(
            output_clip,
            {"c:v": "copy",
             "c:a": "copy"}
        )
    ).execute()

    vf_filters = []

    # FPS
    vf_filters.append(f"fps={fps}")

    # Crop
    if crop:
        vf_filters.append('crop=in_h:in_h')

    # Scale
    vf_filters.append(f"scale={resolution}:-1:flags=lanczos")

    # Subtitle text
    with tempfile.TemporaryDirectory() as tmp:
        if custom_text:
            lines = custom_text.split("\\N")[::-1]

            for i, line in enumerate(lines, start=1):
                # Writing the line to a file helps circumvent ffmpeg's weird escaping rules ¯\_(ツ)_/¯
                # https://ffmpeg.org/ffmpeg-filters.html#Notes-on-filtergraph-escaping
                line_filename = os.path.join(tmp, f'line-{i}.txt')
                with open(line_filename, 'w', encoding='utf-8') as file:
                    file.write(line)

                if font:
                    font_path = font.as_posix().replace(':', r'\:')
                    fontfile_str = f"fontfile='{font_path}':"
                else: fontfile_str = ''

                line_filename = line_filename.replace('\\', '/').replace(':', r'\:')

                # Add the subtitle text to the video
                vf_filters.append(
                    f"drawtext=textfile='{line_filename}':"
                    f"{fontfile_str}"
                    f"fontcolor=white:"
                    f"fontsize={font_size}:"
                    f"x=(w-text_w)/2:y=(h-{i}*line_h):"
                    f"bordercolor=black:borderw=1"
                )

        # Palette
        vf_filters.append("split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse")


        # Join filters
        vf = ",".join(vf_filters)

        try:
            # Create the gif
            (
                FFmpeg()
                .option("y")
                .input(output_clip)
                .output(output_gif, vf=vf)
            ).execute()
        except FFmpegError as e:
            return f'could not create the gif: {e}', False

    return None, True
