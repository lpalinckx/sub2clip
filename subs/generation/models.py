from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from tempfile import TemporaryDirectory
from typing import Optional
from subs.subtitles import Subtitle
from PIL import Image

class VideoFormat(Enum):
    WEBP = 1
    GIF  = 2
    MP4  = 3

@dataclass(frozen=True)
class TextStyle:
    """
    Maps to ASS style of subtitles.
    See http://www.tcax.org/docs/ass-specs.htm for specification
    """
    name: str = "subtitle_style"
    font: str = "Arial"
    font_size: int = 20
    font_color: str = "&H00FFFFFF"
    outline_width: int = font_size/20
    outline_color: str = "&H00000000"
    bold: int = 0 # 0 = regular, 1 = bold
    italic: int = 0 # 0 = regular, 1 = italics
    shadow: int = 0
    alignment: int = 2 # bottom center default

    def build_ass_style_header(self) -> str:
        return (
            "[V4+ Styles]\n"
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,"
            "OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,"
            "ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
            "Alignment,MarginL,MarginR,MarginV,Encoding"
        )

    def build_ass_style(self) -> str:
        return (
            f"Style: {self.name},{self.font},{self.font_size},{self.font_color},&H00000000,"
            f"{self.outline_color},&H00000000,{self.bold},{self.italic},0,0,"
            f"100,100,0,0,1,{self.outline_width},{self.shadow},"
            f"{self.alignment},20,20,20,1"
        )

    def calculate_caption_padding(self, caption_text: str, width: int, height: int) -> str:
        with TemporaryDirectory() as td:
            td = Path(td)
            # td = Path('output/')
            caption_ass = td / "caption.ass"
            png_out = td / "out.png"

            ass_content = (
                "[Script Info]",
                "ScriptType: v4.00+",
                f"PlayResX: {width}",
                f"PlayResY: {height}",
                "",
                self.build_ass_style_header(),
                self.build_ass_style(),
                "",
                "[Events]",
                "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
                f"Dialogue: 0,0:00:00.00,0:00:05.00,{self.name},,0,0,0,,{caption_text}"
            )
            caption_ass.write_text("\n".join(ass_content), encoding="utf-8")

            size = f'{width}x{height}'
            vf = f'subtitles={caption_ass},format=rgba'

            from subs.ffmpeg_helpers import generate_caption_png
            err, ok = generate_caption_png(size, vf, png_out)

            if not ok:
                print(err)
                return -1

            im = Image.open(png_out).convert("RGBA")
            w,h = im.size
            pix = im.load()

            bg = im.getpixel((0,0))[:3]

            top = None
            bottom = None
            for y in range(h):
                row_has = any(pix[x,y][:3] != bg for x in range(w))
                if row_has and top is None:
                    top = y
                if row_has:
                    bottom = y
            if top is None:
                return 0
            measured = bottom - top + 1
            return measured + self.font_size

    def build_caption_filters(self, text: str, width: int, height: int) -> str:
        padding = self.calculate_caption_padding(text, width, height)
        return f"pad=iw:(ih+{padding}):0:{padding}"

@dataclass
class ClipSettings:
    input_path: Path
    clip_path: Path
    output_path: Path
    output_format: VideoFormat
    start: int
    end: int
    fps: int = 20
    width: Optional[int] = None
    height: Optional[int] = None
    resolution: Optional[int] = None
    subtitle_style: TextStyle = None
    caption_style: TextStyle = None
    crop: bool = False
    boomerang: bool = False
    hd_gif: bool = False
    mp4_copy: bool = False
    # Compression settings for FFmpeg
    crf: int = 18
    preset: str = "fast"

    def __post_init__(self):
        if self.start >= self.end:
            raise ValueError("Clip start time cannot be after end time")

        width_set = self.width is not None
        height_set = self.height is not None
        res_set = self.resolution is not None

        if res_set and (width_set or height_set):
            raise ValueError("Either set resolution OR width+height, not both")
        if not res_set and not (width_set and height_set):
            raise ValueError("You must set either resolution OR both width and height")

        if res_set:
            if self.crop:
                self.height = self.width = self.resolution
            else:
                from subs.ffmpeg_helpers import get_dimensions
                (og_w, og_h), ok = get_dimensions(self.input_path)

                if ok:
                    self.height = self.resolution
                    self.width  = 2 * round((og_w*self.height / og_h) / 2)

        ## Check if the filetype set in the filename is the same as the output_format
        parts = self.output_path.split('.')
        if len(parts) > 1:
            if VideoFormat[parts[1].upper()] != self.output_format:
                raise ValueError(f"Output filename had set filetype as '{parts[1]}', but given output_format was {self.output_format}")

        ## Check if self.crop is set and validate the width/height
        if self.crop and not res_set:
            if self.width != self.height:
                raise ValueError("Crop was set to true, but width doesn't match height")

        if not self.subtitle_style:
            self.subtitle_style = TextStyle()

        if not self.caption_style:
            self.caption_style = TextStyle(
                "caption_style",
                font_size=self.subtitle_style.font_size,
                alignment=7
            )

    @property
    def duration(self) -> int:
        return self.end - self.start

    @property
    def duration_s(self) -> float:
        return self.duration / 1000.0

    @property
    def start_s(self) -> float:
        return self.start / 1000.0

    @property
    def end_s(self) -> float:
        return self.end / 1000.0

    def _subtitles_to_ass(self, subs: list[Subtitle], clip_start: int, clip_duration: int, styleName: str) -> str:
        def ms_to_ass_timing(ms: int) -> str:
            cs = int(round(ms / 10)) # centiseconds

            hh = cs // 360_000
            cs %= 360_000

            mm = cs // 6_000
            cs %= 6_000

            ss = cs // 100
            cs %= 100

            return f'{hh}:{mm:02}:{ss:02}.{cs:02}'

        lines: list[str] = []

        for sub in sorted(subs):
            start = ms_to_ass_timing(sub.start + sub.delay - clip_start)
            end   = ms_to_ass_timing(sub.end - clip_start)
            text = "\\N".join(sub.text)

            lines.append(
                f"Dialogue: 0,{start},{end},{styleName},,"
                f"0,0,10,,{text}"
            )

        return "\n".join(lines)

    def _generate_ass(self, subs: list[Subtitle], caption: Subtitle = None) -> str:
        event_header = (
            "[Events]\n"
            "Format: Layer,Start,End,Style,Name,"
            "MarginL,MarginR,MarginV,Effect,Text"
        )

        sub_style = self.subtitle_style.build_ass_style() if subs else ""
        sub_str   = self._subtitles_to_ass(subs, self.start, self.duration, self.subtitle_style.name) if subs else ""
        caption_style = self.caption_style.build_ass_style() if caption else ""
        caption_str   = self._subtitles_to_ass([caption], self.start, self.duration, self.caption_style.name) if caption else ""

        return "\n".join([
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {self.width}",
            f"PlayResY: {self.height}",
            "",
            self.subtitle_style.build_ass_style_header(),
            sub_style,
            caption_style,
            "",
            event_header,
            sub_str,
            caption_str
        ])


    def build_clip_filters(self, subtitles: list[Subtitle] = None, caption: Subtitle = None) -> list[str]:
        vf_filters = []

        if self.boomerang:
            vf_filters.append("[0]reverse[r];[0][r]concat=n=2:v=1:a=0")

        vf_filters.append(f'fps={self.fps}')

        if self.crop:
            vf_filters.append('crop=in_h:in_h')

        vf_filters.append(f'scale={self.width}:{self.height}:flags=lanczos')

        if caption:
            vf_filters.append(self.caption_style.build_caption_filters("\\N".join(caption.text), self.width, self.height))


        with TemporaryDirectory() as tmp:
            ass = self._generate_ass(subtitles, caption)
            ass_file = Path('output/') / 'sub.ass'
            ass_file.write_text(ass, encoding='utf-8')

            vf_filters.append(f"subtitles={ass_file.resolve()}")

        if self.output_format == VideoFormat.GIF:
            # Palette
            if self.hd_gif:
                vf_filters.append("split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse")
            else:
                vf_filters.append("split[s0][s1];[s0]palettegen=max_colors=32[p];[s1][p]paletteuse=dither=bayer")

        return vf_filters
