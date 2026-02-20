import json
import time
import functools
import logging
import pysubs2
from ffmpeg import FFmpeg, FFmpegError
from sub2clip.generation import ClipSettings
from pathlib import Path

# module logger
logger = logging.getLogger(__name__)


def timeit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except Exception:
            elapsed = time.perf_counter() - start
            msg = f"{func.__name__} raised after {elapsed:.3f}s"
            logger.debug(msg)
            if logger.isEnabledFor(logging.DEBUG):
                print(msg)
            raise
        else:
            elapsed = time.perf_counter() - start
            msg = f"{func.__name__} took {elapsed:.3f}s"
            logger.debug(msg)
            if logger.isEnabledFor(logging.DEBUG):
                print(msg)
            return result

    return wrapper


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

@timeit
def generate_caption_png(size: str, vf, png_out: Path) -> tuple[None|str, bool]:
    try:
        (
            FFmpeg()
            .option("y")
            .option("f", value="lavfi")
            .option("i", value=f"color=0xFF00FF:size={size}:duration=1")
            .option("vf", value=vf)
            .option("frames:v", value="1")
            .output(png_out)
        ).execute()
    except FFmpegError as e:
        return f'FFmpeg error during caption generation: {e}. Command = {_return_ffmpeg_command(e)}', False
    return None, True

@timeit
def get_dimensions(path: Path) -> tuple[tuple[int,int]|str, bool]:
    try:
        ffmpeg = (
            FFmpeg(executable="ffprobe")
            .input(path)
            .option('select_streams', value='v:0')
            .option('show_entries', value='stream=width,height')
            .option('of', value="csv=p=0")
        )
        res = ffmpeg.execute().decode().strip()
        w, h = map(int, res.split(','))

        return (w, h), True
    except FFmpegError as e:
        return f'FFmpeg error during ffprobe: {e}. Command = {_return_ffmpeg_command(e)}', False



@timeit
def run_ffmpeg(input: Path, output: Path, filters=None) -> tuple[None|str, bool]:
    ffmpeg = FFmpeg().option('y').input(input)

    if filters:
        ffmpeg = ffmpeg.output(output, {'filter_complex': filters, 'loop': 0})

    try:
        ffmpeg.execute()
    except FFmpegError as e:
        return f'FFmpeg error: {e}. command = {_return_ffmpeg_command(e)}', False
    return None, True


@timeit
def extract_subtitles(input: Path, output: Path, track: int) -> tuple[pysubs2.SSAFile | str, bool]:
    try:
        (
            FFmpeg()
            .option("y")
            .input(input)
            .output(
                output,
                map=[f'0:s:{track}'],
                an=None,
                vn=None)
        ).execute()
    except FFmpegError as e:
        return f'Could not extract subtitles from video {input} at sub track {track}: {e}', False

    if Path(output).exists():
        subs = pysubs2.load(output)

        return subs, True
    else:
        return f'Could not extract subtitles from video {input} at sub track {track}', False

@timeit
def get_subtitle_lang_track(input: Path, langs: list[str], include_cc: bool = False) -> [str|int, bool]:
    ffprobe = FFmpeg(executable="ffprobe").input(input, print_format="json", show_streams=None)
    media = json.loads(ffprobe.execute())

    sub_streams = [
        stream for stream in media.get("streams", [])
        if stream["codec_type"] == 'subtitle'
    ]

    non_sub_streams = [
        stream for stream in media.get("streams", [])
        if stream["codec_type"] != 'subtitle'
    ]

    if len(sub_streams) == 0:
        return "No subtitle streams found for " + input.as_posix(), False

    target_stream = None
    for lang in langs:
        for stream in sub_streams:
            tags = stream.get('tags', {})
            sub_lang = tags.get('language', '')
            title = tags.get('title', '').lower()

            if lang != sub_lang:
                continue

            if include_cc or not any(k in title for k in ('sdh', 'cc', 'hearing impaired')):
                target_stream = stream
                break

        if target_stream:
            break

    if not target_stream:
        return "No subtitle stream exists for any of the requested languages: " + ','.join(langs), False

    return int(target_stream.get('index'))-len(non_sub_streams), True

@timeit
def create_clip(clip_settings: ClipSettings) -> tuple[str|None, bool]:
    def has_video_stream(path):
        ffprobe = FFmpeg(executable="ffprobe").input(path, print_format="json", show_streams=None)
        media = json.loads(ffprobe.execute())

        return any(
            stream.get("codec_type") == "video"
            for stream in media.get("streams", [])
        )

    ffmpeg = (
        FFmpeg().option('y')
                .input(clip_settings.input_path)
                .option('ss', value=clip_settings.start_s)
                .option('t', value=clip_settings.duration_s)
                .output(clip_settings.clip_path, { 'c': 'copy' })
    )

    try:
        ffmpeg.execute()
        if not has_video_stream(clip_settings.clip_path):
            (
                FFmpeg().option('y')
                        .input(clip_settings.input_path)
                        .option('ss', value=clip_settings.start_s)
                        .option('t', value=clip_settings.duration_s)
                        .output(clip_settings.clip_path, { 'c:v': 'libx265', 'crf': clip_settings.crf, 'preset': clip_settings.preset })
            ).execute()
    except FFmpegError as e:
        return f'FFmpegError during clip creation: {e}', False
    return None, True
