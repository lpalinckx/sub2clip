import tempfile
import logging
from pathlib import Path
from pysubs2 import (SSAFile)
from .ffmpeg import (run_ffmpeg, extract_subtitles, create_clip)
from subs.subtitles import Subtitle
from subs.generation import (ClipSettings, TextStyle)

def extract_subs(video_path: Path, subtitle_track: int = 0) -> tuple[SSAFile | str, bool]:
    with tempfile.TemporaryDirectory() as tmp:
        output_path = Path(tmp) / 'subs.srt'
        res, ok = extract_subtitles(video_path, output_path, subtitle_track)

        if not ok:
            return res, False
        return res, True

def _subtitles_to_ass(subs: list[Subtitle], clip_start: int, clip_duration: int) -> str:
    def ms_to_ass_timing(ms: int) -> str:
        cs = int(round(ms / 10)) # centiseconds

        hh = cs // 360_000
        cs %= 360_000

        mm = cs // 6_000
        cs %= 6_000

        ss = cs // 100
        cs %= 100

        return f'{hh}:{mm:02}:{ss:02}.{cs:02}'

    header = (
        "[Events]\n"
        "Format: Layer,Start,End,Style,Name,"
        "MarginL,MarginR,MarginV,Effect,Text\n"
    )

    lines: list[str] = []

    for sub in sorted(subs):
        start = ms_to_ass_timing(sub.start + sub.delay - clip_start)
        end   = ms_to_ass_timing(sub.end - clip_start)
        text = "\\N".join(sub.text)

        lines.append(
            f"Dialogue: 0,{start},{end},subStyle,,"
            f"0,0,10,,{text}"
        )

    return header + "\n".join(lines)

def _generate_ass(subs: list[Subtitle], clip_settings: ClipSettings) -> str:
    return "\n".join([
        "[Script Info]",
        "ScriptType: v4.00+\n",
        clip_settings.text_style.build_ass_style_header(),
        clip_settings.text_style.build_ass_style(),
        "",
        _subtitles_to_ass(subs, clip_settings.start, clip_settings.duration)
    ])


def generate(clip_settings: ClipSettings, subtitles: list[Subtitle], caption: Subtitle) -> tuple[str|None, bool]:

    err, ok = create_clip(clip_settings)
    if not ok:
        return err, False

    with tempfile.TemporaryDirectory() as tmp:
        ass_file = None
        if subtitles:
            # ass_file = Path(tmp) / 'sub.ass'
            ass_file = Path('output/') / 'sub.ass'
            ass_file.write_text(
                _generate_ass(subtitles, clip_settings),
                encoding="utf-8"
            )

        vf_caption = None
        if caption:
            vf_caption = clip_settings.textStyle.build_drawtext_filters(caption.text, True, tmp)

        vf_filters = clip_settings.build_clip_filters(sub_file=ass_file, vf_caption=vf_caption)

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