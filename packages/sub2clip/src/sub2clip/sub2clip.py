from pathlib import Path
from pysubs2 import (SSAFile)
from .ffmpeg_helpers import (run_ffmpeg, extract_subtitles, create_clip)
from sub2clip.subtitles import Subtitle
from sub2clip.generation import (ClipSettings)
from tempfile import TemporaryDirectory

def extract_subs(video_path: Path, subtitle_track: int = 0) -> tuple[list[Subtitle] | str, bool]:
    """Extracts the subtitles from the given Path. Subtitle track can be specified.

    Args:
        video_path (Path): Input video
        subtitle_track (int, optional): Specific track to extract from the video, see FFmpeg for more details. Defaults to 0.

    Returns:
        tuple[list[Subtitle] | str, bool]:
            - [list[Subtitle], True] when subtitle extraction succeeded.
            - [str, False] when subtitle extraction failed, str being the error message
    """
    with TemporaryDirectory() as tmp:
        output_path = Path(tmp) / 'subs.srt'
        res, ok = extract_subtitles(video_path, output_path, subtitle_track)

        subs = [Subtitle(
            start=ssa.start,
            end=ssa.end,
            text=[line for line in ssa.text.split("\\N")]
        ) for ssa in res]

        if not ok:
            return res, False
        return subs, True

def generate(clip_settings: ClipSettings, subtitles: list[Subtitle], caption: Subtitle = None) -> tuple[str|None, bool]:
    """Generate a clip with the given clipsettings and subtitles. Caption is optional.

    Args:
        clip_settings (ClipSettings): ClipSettings to use. See ClipSettings for explanation
        subtitles (list[Subtitle]): List of subtitles to render in the clip.
        caption (Subtitle, optional): Caption to display above the clip, lasts for the entire clip. Defaults to None.

    Returns:
        tuple[str|None, bool]:
            - [None, True] when generation succeeeded.
            - [str, False] when clip generation failed, str being the error message.
    """
    err, ok = create_clip(clip_settings)
    if not ok:
        return err, False

    with TemporaryDirectory() as tmp:
        vf_filters = clip_settings.build_clip_filters(tmp, subtitles, caption)
        vf = ",".join(vf_filters)

        err, ok = run_ffmpeg(clip_settings.clip_path, clip_settings.output_path, vf)
        if not ok:
            return err, False

        if clip_settings.mp4_copy:
            ## TODO
            # err, ok =
            if not ok:
                return err, False
        return None, True