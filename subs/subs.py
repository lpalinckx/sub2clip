import pysubs2
import tempfile
import os
from ffmpeg import (FFmpeg, FFmpegError)

# Functions in this library return a second boolean value indicating success/failure
# In case of failure, the first return value is the error message

def _return_ffmpeg_command(ffmpeg):
    """Prints the complete FFmpeg command with quotation marks around the filters tag, making copy-pasting into a shell very easy

    Args:
        ffmpeg (FFmpeg or FFmpegError): FFmpeg object containing 'arguments' field
    """
    args = ffmpeg.arguments
    if '-filter_complex' in args:
        filter_idx = args.index('-filter_complex') + 1
        args[filter_idx] = f'"{args[filter_idx]}"'
    return ' '.join(args)

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
            return f'could not extract subtitles from video {video_path}: {e}. FFmpeg command = {_return_ffmpeg_command(e)}', False

        if os.path.exists(output_path):
            return pysubs2.load(output_path), True
        else:
            return f'could not extract subtitles from video {video_path}', False

def text_filters(tmp, text, font, font_size, is_caption=False):
    """Returns the drawtext filters with the corresponding text and font settings

    Args:
        tmp (TemporaryDirectory): Temp directory of the system
        text (str): Text string to add, can contain multiple lines
        font (str): Path to the font to be used
        font_size (int): Font size used
        is_caption (bool, optional): Determines whether to put the text in the caption area or as subtitles. Defaults to False.
    """
    vf = []

    def ffmpeg_friendly_path(path):
        return path.replace('\\', '/').replace(':', r'\:')

    # Extract newlines
    lines = text.split("\\N")[::-1]

    # Lines are stored in reverse order, make sure they are in order for the caption text
    lines = list(reversed(lines)) if is_caption else lines

    # Calculate padding
    padding = (2 + text.count("\\N")) * font_size if is_caption else 0
    if is_caption:
        vf.append(f"pad=iw:(ih+{padding}):0:{padding}")

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

        vf.append(
            f"drawtext=textfile='{text_file}':"
            f"{fontfile_str}"
            f"fontcolor=white:"
            f"fontsize={font_size}:"
            f"x={x}:y={y}:"
            f"bordercolor=black:borderw={font_size/20}"
        )
    return vf

def _run_ffmpeg(input_path, output_path, filters=None, start_time=None, duration=None):
    """Runs FFmpeg command with optional filters, start_time and duration. Always overwrites the output_path

    Args:
        input_path (str): Input video file path
        output_path (str): Output video file path
        filters (str, optional): FFmpeg filters. Defaults to None.
        start_time (float, optional): Start time in seconds. Defaults to None.
        duration (float, optional): Duration in seconds. Defaults to None.

    Returns:
        Tuple: (None, True) when FFmpeg command succeeded or (str, False) when unsuccessful, with the error msg in str
    """
    ffmpeg = FFmpeg().option('y').input(input_path)

    if start_time:
        ffmpeg = ffmpeg.option('ss', value=start_time)

    if duration:
        ffmpeg = ffmpeg.option('t', value=duration)

    if filters:
        ffmpeg = ffmpeg.output(output_path, {'filter_complex': filters, 'loop': 0})
    else:
        ffmpeg = ffmpeg.output(output_path, {'c:v': 'copy', 'c:a': 'copy'})

    try:
        ffmpeg.execute()
    except FFmpegError as e:
        return f'FFmpeg error: {e}. Command = {_return_ffmpeg_command(e)}', False
    return None, True

def concat_mp4(mp4s, output):
    """Concats the given mp4s into a single mp4

    Args:
        mp4s ([str]): List of paths for each mp4
        output (str): Output path for the concatted mp4

    Returns:
        Tuple: (None, True) when concat was successful or (str, False) when unsuccessful, the str value is the error message.
    """
    with tempfile.TemporaryDirectory() as tmp:
        to_concat = os.path.join(tmp, 'mp4list.txt')
        with open(to_concat, 'w') as f:
            for mp4 in mp4s:
                f.write(f"file '{mp4}'\n")

        try:
            (
                FFmpeg()
                .option('y')
                .option('f', 'concat')
                .option('safe', 0)
                .input(to_concat)
                .output(
                    output,
                    {
                        'c:v': 'copy',
                        'c:a': 'copy'
                    }
                )
            ).execute()
        except FFmpegError as e:
            return f"Could not concat mp4s: {e}. FFmpeg command = {' '.join(e.arguments)}", False

        return None, True

def mp4_to_vid(mp4, output_format, output_path, caption, fps, crop, resolution, fancy_colors=False):
    """Converts the given mp4 to another given videoformat

    Args:
        mp4 (str): Path to the mp4 file
        output_format (str): GIF or WEBP
        output_path (str): Output path
        caption (str): Caption to put on top
        fps (int): Frames per second
        crop (boolean): Crop the output to a square
        resolution (int): Output resolution
        fancy_colors (boolean, optional): include all colors in gif, greatly increases GIF file size

    Returns:
        Tuple: (None, True) if the conversion was successful. (str, False) when unsuccessful, the str contains the error message
    """
    filters = [f'fps={fps}']

    if crop:
        filters.append('crop=in_h:in_h')

    filters.append(f'scale={resolution}:-1:flags=lanczos')

    # Palette
    if (output_format == 'gif'):
        if fancy_colors:
            filters.append("split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse")
        else:
            filters.append("split[s0][s1];[s0]palettegen=max_colors=32[p];[s1][p]paletteuse=dither=bayer")

    fltrs = ','.join(filters)

    return _run_ffmpeg(mp4, output_path, filters=fltrs)

def generate_sequence(source_video, output_format, video_settings, output_path, output_mp4, caption, fps, crop, resolution, fancy_colors=False):
    """Generates a single GIF from multiple input videos

    Args:
        source_video (str): Path to source video to create clips from
        output_format (str): GIF or WEBP
        video_settings (list): List containing entries for each video with the following structure:
            {
                'start_time': float,
                'end_time': float,
                'custom_text': str,
                'font': str
                'font_size': int
            }
        output_path (str): output path of the video
        output_mp4 (str): output path of the mp4 version
        caption (str): caption to use
        fps (int): Frames per second
        crop (bool): Crop the video to a square (1:1 aspect ratio)
        resolution (int): Output resolution of the video
        fancy_colors (bool, optional): include all colors in gif, greatly increases gif size

    Returns:
        Tuple: (None, True) when video creation was succesful or (str, False) when unsuccesful, the str value is the error message.
    """
    with tempfile.TemporaryDirectory() as tmp:
        mp4_output = f'output/output.mp4'
        vid_output = f'output/output.{output_format}'
        clips = []

        for idx, video in enumerate(video_settings):
            clip = os.path.join(tmp, f'clip{idx}.mp4')
            mp4  = os.path.join(tmp, f'mp4{idx}.mp4')

            nxt = video_settings[idx+1] if idx < len(video_settings)-1 else None
            end = nxt['start_time'] if nxt else video['end_time']

            err, ok = generate_mp4(
                start_time=video['start_time'],
                end_time=end,
                output_clip=clip,
                output_mp4=mp4,
                custom_text=video['custom_text'],
                caption='',
                video_path=source_video,
                fps=fps,
                crop=crop,
                resolution=resolution,
                font=video['font'],
                font_size=video['font_size']
            )

            if ok:
                clips.append(mp4)
            else: return err

        # Concat the mp4s
        err, ok = concat_mp4(clips, mp4_output)

        if ok:
            err, ok = mp4_to_vid(
                mp4=mp4_output,
                output_format=output_format,
                output_path=vid_output,
                caption=caption,
                fps=fps,
                crop=crop,
                resolution=resolution,
                fancy_colors=fancy_colors
            )
        else: return err, False
    return None, True

# Abstractions
def generate_gif(start_time, end_time, output_clip, output_gif, custom_text, caption, video_path, fps, crop, boomerang, resolution, font, font_size, fancy_colors, mp4_copy=False, output_mp4=""):
    return generate_video(start_time, end_time, output_clip, output_gif, custom_text, caption, video_path, fps, crop, boomerang, resolution, font, font_size, fancy_colors, "gif", mp4_copy, output_mp4)
def generate_webp(start_time, end_time, output_clip, output_webp, custom_text, caption, video_path, fps, crop, boomerang, resolution, font, font_size, mp4_copy=False, output_mp4=""):
    return generate_video(start_time, end_time, output_clip, output_webp, custom_text, caption, video_path, fps, crop, boomerang, resolution, font, font_size, False, "webp", mp4_copy, output_mp4)
def generate_mp4(start_time, end_time, output_clip, output_mp4, custom_text, caption, video_path, fps, crop, resolution, font, font_size):
    return generate_video(start_time, end_time, output_clip, output_mp4, custom_text, caption, video_path, fps, crop, False, resolution, font, font_size)

def generate_video(start_time, end_time, output_clip, output_path, custom_text, caption, input_path, fps, crop, boomerang, resolution, font, font_size, fancy_colors=False, format_type="webp", mp4_copy=False, output_mp4=""):
    """Generate an animation (GIF, WEBP, or MP4) from a video file using FFmpeg.

    Args:
        start_time (float): Start time in seconds.
        end_time (float): End time in seconds.
        output_clip (str): Output path of the clip.
        output_path (str): Output path of the animation (gif/webp).
        custom_text (str): Subtitle text to embed.
        caption (str): Caption text to embed.
        input_path (str): Path to the input video.
        fps (int): Frames per second.
        crop (bool): Crop the video to a square.
        boomerang (bool): Reverse the animation and append to the end.
        resolution (int): Output resolution.
        font (str): Path to the font.
        font_size (int): Font size.
        fancy_colors (bool): Include full colors (applies to GIFs, increases file size).
        format_type (str): Animation format - "gif" or "webp".
        mp4_copy (bool, optional): Create an MP4 copy with embedded text.
        output_mp4 (str, optional): Output path of the MP4 file.

    Returns:
        Tuple: (None, True) when successful, (error_message, False) when unsuccessful.
    """
    if start_time >= end_time:
        return f'duration must be at least 1 second', False

    duration = end_time - start_time
    err, ok = _run_ffmpeg(input_path, output_clip, start_time=start_time, duration=duration)
    if not ok:
        return err, False

    with tempfile.TemporaryDirectory() as tmp:
        vf_filters = []
        vf_caption = vf_text = None
        # Add text overlays
        if caption:
            vf_caption = text_filters(tmp, caption, font, font_size, is_caption=True)

        if custom_text:
            vf_text = text_filters(tmp, custom_text, font, font_size, is_caption=False)

        vf_filters += build_ffmpeg_filters(fps, crop, resolution, boomerang, fancy_colors, format_type, vf_caption=vf_caption, vf_text=vf_text)

        vf = ",".join(vf_filters)

        err, ok = _run_ffmpeg(output_clip, output_path, filters=vf)
        if not ok:
            return err, False

        if mp4_copy:
            err, ok = _run_ffmpeg(output_clip, output_mp4, filters=','.join(vf_filters[:-1]))  # Remove palette filter for MP4
            if not ok:
                return err, False

    return None, True

def build_ffmpeg_filters(fps, crop, resolution, boomerang, fancy_colors, format_type, vf_caption=None, vf_text=None):
    """Returns array of ffmpeg filters

    Args:
        fps (int): Frames per second
        crop (bool): Crop to square
        resolution (int): Output resolution
        boomerang (bool): Append the reverse of the clip
        fancy_colors (bool): Include full colors (applies to GIFs, increases file size).
        format_type (str): Animation format - "gif" or "webp".
        vf_caption (list): List containing filters for the caption text
        vf_text (list): List containing filters for the subtitle text
    """
    vf_filters = []

    if boomerang:
        vf_filters.append("[0]reverse[r];[0][r]concat=n=2:v=1:a=0")

    vf_filters.append(f'fps={fps}')

    if crop:
        vf_filters.append('crop=in_h:in_h')

    vf_filters.append(f'scale={resolution}:-1:flags=lanczos')

    if vf_caption:
        vf_filters += vf_caption

    if vf_text:
        vf_filters += vf_text

    if format_type == 'gif':
        # Palette
        if fancy_colors:
            vf_filters.append("split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse")
        else:
            vf_filters.append("split[s0][s1];[s0]palettegen=max_colors=32[p];[s1][p]paletteuse=dither=bayer")

    return vf_filters