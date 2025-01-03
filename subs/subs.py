import pysubs2
import tempfile
import os
from ffmpeg import (FFmpeg, FFmpegError)

# Functions in this library return a second boolean value indicating success/failure
# In case of failure, the first return value is the error message

def extract_subs(video_path):
    """Extract subs with FFmpeg to a tmp file (pysubs2 _only_ works with files).
    Load them with pysubs2 and return the result.
    The tmp dir is cleaned up automatically.

    Args:
        video_path (str): Path to a video containing subtitles

    Returns:
        Tuple: (SSAFile, True) when the sub extraction succeeded or (str, False) when unsuccesful, with str being the error message.
    """
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

def add_text(tmp, vf_filters, text, font, font_size, padding=0, is_caption=False):
    """Adds the drawtext filters to vf_filters with the corresponding text and font settings

    Args:
        tmp (TemporaryDirectory): Temp directory of the system
        vf_filters (list): List of vf_filters to be applied to the video
        text (str): Text string to add, can contain multiple lines
        font (str): Path to the font to be used
        font_size (int): Font size used
        padding (int, optional): Padding used in the caption. Defaults to 0.
        is_caption (bool, optional): Determines whether to put the text in the caption area or as subtitles. Defaults to False.
    """
    def ffmpeg_friendly_path(path):
        return path.replace('\\', '/').replace(':', r'\:')

    # Extract newlines
    lines = text.split("\\N")[::-1]

    # Lines are stored in reverse order, make sure they are in order for the caption text
    lines = list(reversed(lines)) if is_caption else lines

    # Calculate offset for caption
    text_height    = len(lines) * font_size
    padding_offset = (padding - text_height)/2

    for i, line in enumerate(lines, start=1):
        filename = f"caption-{i}.txt" if is_caption else f"subtitle-{i}.txt"
        # Writing the line to a file helps circumvent ffmpeg's weird escaping rules ¯\_(ツ)_/¯
        # https://ffmpeg.org/ffmpeg-filters.html#Notes-on-filtergraph-escaping
        text_file = os.path.join(tmp, filename)

        with open(text_file, 'w', encoding='utf-8') as file:
            file.write(line)

        # Make paths FFmpeg-friendly
        fontfile_str = f"fontfile='{ffmpeg_friendly_path(font.as_posix())}':" if font else ''
        text_file = ffmpeg_friendly_path(text_file)

        # Text offsets
        x = "10" if is_caption else "(w-text_w)/2"
        y = f"{padding_offset} + {i}*line_h - line_h" if is_caption else f"(h-{i}*line_h)"

        vf_filters.append(
            f"drawtext=textfile='{text_file}':"
            f"{fontfile_str}"
            f"fontcolor=white:"
            f"fontsize={font_size}:"
            f"x={x}:y={y}:"
            f"bordercolor=black:borderw=1"
        )

def generate_gif(start_time, end_time, output_clip, output_gif, custom_text, caption, video_path, fps, crop, boomerang, resolution, font, font_size):
    """Generate a GIF from a video file using FFmpeg

    Args:
        start_time (float): Start time, in seconds
        end_time (float): End time, in seconds
        output_clip (str): Output path of the clip
        output_gif (str): Output path of the gif
        custom_text (str): Subtitle text to embed in the gif
        caption (str): Caption text to embed in the gif
        video_path (str): Path to the input video
        fps (int): Frames per second to use
        crop (bool): Crop the video to a square (1:1 aspect ratio)
        boomerang (bool): "Boomerang" the gif; the reverse of the original gif is appended to the end
        resolution (int): Output resolution of the gif
        font (str): Path to the font to use
        font_size (int): Size of the font

    Returns:
        Tuple: (None, True) when gif creation was succesful or (str, False) when unsuccesful, the str value is the error message.
    """
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

    if boomerang:
        vf_filters.append("[0]reverse[r];[0][r]concat=n=2:v=1:a=0")

    # FPS
    vf_filters.append(f"fps={fps}")

    # Crop
    if crop:
        vf_filters.append('crop=in_h:in_h')

    # Scale
    vf_filters.append(f"scale={resolution}:-1:flags=lanczos")

    with tempfile.TemporaryDirectory() as tmp:
        # Caption text
        if caption:
            # Add black bars to the top of the gif for the caption
            print(caption.count("\\N"))
            padding = (2 + caption.count("\\N")) * font_size
            print(padding)
            vf_filters.append(
                f"pad=iw:(ih+{padding}):0:{padding}"
            )

            add_text(tmp, vf_filters, caption, font, font_size, padding, is_caption=True)

        # Subtitle text
        if custom_text:
            add_text(tmp, vf_filters, custom_text, font, font_size, is_caption=False)

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
                .output(output_gif, {'filter_complex': vf})
            ).execute()
        except FFmpegError as e:
            return f'could not create the gif: {e}', False

    return None, True
