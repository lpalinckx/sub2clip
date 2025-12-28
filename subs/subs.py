from pathlib import Path
from pysubs2 import (SSAFile)
from .ffmpeg_helpers import (run_ffmpeg, extract_subtitles, create_clip)
from subs.subtitles import Subtitle
from subs.generation import (ClipSettings)
from tempfile import TemporaryDirectory

def extract_subs(video_path: Path, subtitle_track: int = 0) -> tuple[SSAFile | str, bool]:
    with TemporaryDirectory() as tmp:
        output_path = Path(tmp) / 'subs.srt'
        res, ok = extract_subtitles(video_path, output_path, subtitle_track)

        if not ok:
            return res, False
        return res, True

def generate(clip_settings: ClipSettings, subtitles: list[Subtitle], caption: Subtitle = None) -> tuple[str|None, bool]:

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