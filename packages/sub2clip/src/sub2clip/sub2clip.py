from pathlib import Path
from .ffmpeg_helpers import (run_ffmpeg, extract_subtitles, get_subtitle_lang_track, create_clip)
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

        if not ok:
            return res, False

        subs = [Subtitle(
            start=ssa.start,
            end=ssa.end,
            text=ssa.text.split("\\N")
        ) for ssa in res]

        for i, sub in enumerate(subs):
            sub.prv = subs[i-1] if i > 0 else None
            sub.nxt = subs[i+1] if i < len(subs)-1 else None

        return subs, True

def extract_subs_by_language(video_path: Path, languages: list[str], include_cc: bool = False) -> tuple[list[Subtitle] | str, bool]:
    """Extracts subtitles from the given Path based on the given languages.
    Languages must be given as a ISO 639 language code.
    If no subtitles are found matching any of the given languages, an error is thrown.

    Args:
        video_path (Path): Input video
        languages (list[str]): List of languages, priotizes left to right. Must be ISO 639 language code.
        include_cc (bool, optional): Whether to include subtitles marked as Closed Captions, Hearing Impaired or similar. Defaults to False.

    Returns:
        tuple[list[Subtitle] | str, bool]:
            - [list[Subtitle], True] when subtitle extraction succeeded.
            - [str, False] when subtitle extraction failed, str being the error message
    """
    idx, ok = get_subtitle_lang_track(video_path, languages)

    if not ok:
        return idx, False

    subs, ok = extract_subs(video_path, idx)
    if not ok:
        return subs, False
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