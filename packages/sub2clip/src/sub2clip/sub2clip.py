from pathlib import Path
from .ffmpeg_helpers import (run_ffmpeg, extract_subtitles, get_subtitle_lang_track, create_clip, create_thumbnail)
from sub2clip.subtitles import Subtitle
from sub2clip.generation import (ClipSettings)
from tempfile import TemporaryDirectory
from returns.result import Result, Success, Failure
import pysubs2

def extract_subs(video_path: Path, subtitle_track: int = 0) -> Result[list[Subtitle], str]:
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

        res = extract_subtitles(video_path, output_path, subtitle_track)

        def to_subs(file: pysubs2.SSAFile) -> list[Subtitle]:
            subs = [Subtitle(
                start=ssa.start,
                end=ssa.end,
                text=ssa.text.replace("\\N", "\n")
            ) for ssa in file]

            for i, sub in enumerate(subs):
                sub.prv = subs[i-1] if i > 0 else None
                sub.nxt = subs[i+1] if i < len(subs)-1 else None

            return subs

        return res.map(to_subs)

def extract_subs_by_language(video_path: Path, languages: list[str], include_cc: bool = False) -> Result[list[Subtitle], str]:
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
    return Result.do(
        extracted_subs
        for idx in get_subtitle_lang_track(video_path, languages)
        for extracted_subs in extract_subs(video_path, idx)
    )
    # idx = get_subtitle_lang_track(video_path, languages)
    # idx.do()
    # return idx.map(lambda idx: extract_subs(video_path, idx))
    # match idx:
    #     case Success(idx):
    #         return extract_subs(video_path, idx)
    #     case Failure(err):
    #         return Failure(err)
    #     case _:
    #         return Failure("unreachable")

def generate(clip_settings: ClipSettings, subtitles: list[Subtitle], caption: Subtitle | None = None, thumbnail: bool = False) -> Result[None, str]:
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
    if thumbnail:
        err = create_thumbnail(clip_settings)
        match err:
            case Failure(err):
                return Failure(err)
    else:
        err = create_clip(clip_settings)
        match err:
            case Failure(err):
                return Failure(err)

    with TemporaryDirectory() as tmp:
        vf_filters = clip_settings.build_clip_filters(tmp, subtitles, caption)
        vf = ",".join(vf_filters)

        err = run_ffmpeg(clip_settings.clip_path, clip_settings.output_path, vf)
        match err:
            case Failure(err):
                return Failure(err)

        if clip_settings.mp4_copy:
            ## TODO
            # err, ok =
            match err:
                case Failure(err):
                    return Failure(err)
        return Success(None)