from dataclasses import (dataclass, field)
from pathlib import Path
from enum import Enum
from tempfile import TemporaryDirectory
from typing import Optional
from subs.subtitles import Subtitle
from PIL import Image

class VideoFormat(Enum):
    """Supported formats to generate clips
    """
    WEBP = 1
    GIF  = 2
    MP4  = 3

@dataclass(frozen=True)
class TextStyle:
    """Maps to ASS style of subtitles.
    See http://www.tcax.org/docs/ass-specs.htm for specification

    All properties are optional in this class, the default values are suited for subtitles.

    Properties:
        name (str): Name of the style, used in ASS file
        font (str): Name of the font, used in ASS file
        font_size (int): Size of the font
        font_color (str): Color to use for the font. Defaults to white
        outline_width (int): Size of the outline for the font. Defaults to the font_size/20
        outline_color (str): Color to use for the outline. Defaults to black
        bold (int): Whether to make the font bold or not (0 or 1)
        italic (int): Whether to make the font italic or not (0 or 1)
        shadow (int): Whether to add a show or not (0 or 1)
        alignment (int): Position of the text string, see ASS specification for values. Defaults to bottom center (2).
        margin_l (int): Left margin
        margin_r (int): Right margin
        margin_v (int): Vertical margin
    """
    name: str = "subtitle_style"
    font: str = "Arial"
    font_size: int = 20
    font_color: str = "&H00FFFFFF"
    _outline_width: Optional[int] = field(default=None, repr=False)
    outline_color: str = "&H00000000"
    bold: int = 0 # 0 = regular, 1 = bold
    italic: int = 0 # 0 = regular, 1 = italics
    shadow: int = 0
    alignment: int = 2 # bottom center default
    margin_l: int = 0
    margin_r: int = 0
    margin_v: int = 10

    @property
    def outline_width(self) -> int:
        return (
            self.font_size // 20
            if self._outline_width is None
            else self._outline_width
        )

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
            f"{self.alignment},{self.margin_l},{self.margin_r},{self.margin_v},1"
        )

    def calculate_caption_padding(self, caption_text: str, width: int, height: int) -> str:
        with TemporaryDirectory() as td:
            td = Path(td)
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
                f"Dialogue: 0,0:00:00.00,0:00:05.00,{self.name},,{self.margin_l},{self.margin_r},{self.margin_v},,{caption_text}"
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
            return measured + self.margin_v*2

    def build_caption_filters(self, text: str, width: int, height: int) -> tuple[str, int]:
        padding = self.calculate_caption_padding(text, width, height)
        return f"pad=iw:(ih+{padding}):0:{padding}", padding

@dataclass
class ClipSettings:
    """Collection of settings to use during clip generation

    Properties:
        input_path (Path): source video to use
        clip_path (Path): location where the mp4 clip will be stored
        output_path (Path): location of the generated clip
        output_format (VideoFormat): Format to use
        start (int): Start time of the clip, in milliseconds
        end (int): End time of the clip, in milliseconds
        fps (int): Frames per second to use. Defaults to 20
        width (int, optional): Output clip width, in pixels. Can only be set if height is also set.
        height (int, optional): Output clip height, in pixels. Can only be set if width is also set.
        resolution (int, optional): Output clip height, let FFmpeg automatically calculate width keeping aspect ratio
        subtitle_style (TextStyle, optional): Style to use for the subtitles
        caption_style (TextStyle, optional): Style to use for the caption
        crop (bool, optional): Crop the clip to a square (e.g. 200x200). Default False.
        boomerang (bool, optional): Append the reverse of the clip. Default False.
        hd_gif (bool, optional): Use high quality colors for the GIF, increasing file size significantly. Default False.
        mp4_copy (bool, optional): Generate a copy mp4 (with burnt-in caption/subtiles). Default False.
        crf (int, optional): Constant Rate Factor, value used by FFmpeg for re-encoding. Default 18.
        preset (str, optional): Re-encoding preset used by FFmpeg. Default 'fast'.

    There are several checks that happen after creating a ClipSettings instance.
    If there is an invalid state, a ValueError is thrown.
    Raises:
        ValueError: when start time is set past end time
        ValueError: when resolution is set and either width or height is set
        ValueError: when resolution is not set and either width or height is not set
        ValueError: when the output path has the extension set to something else than the given VideoFormat
        ValueError: when crop was set to true, but the given width and height don't match.
    """
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
        ftype = self.output_path.suffix[1::]
        if VideoFormat[ftype.upper()] != self.output_format:
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
                alignment=7,
                margin_l=15,
                margin_r=0,
                margin_v=10
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

    def _subtitles_to_ass(self, subs: list[Subtitle], clip_start: int, style: TextStyle) -> str:
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
                f"Dialogue: 0,{start},{end},{style.name},,"
                f"{style.margin_l},{style.margin_r},{style.margin_v},,{text}"
            )

        return "\n".join(lines)

    def _generate_ass(self, subs: list[Subtitle], caption: Subtitle | list[Subtitle] = None, padding: int = 0) -> str:
        event_header = (
            "[Events]\n"
            "Format: Layer,Start,End,Style,Name,"
            "MarginL,MarginR,MarginV,Effect,Text"
        )

        sub_style = self.subtitle_style.build_ass_style() if subs else ""
        sub_str = self._subtitles_to_ass(subs, self.start, self.subtitle_style) if subs else ""

        caption_style = ""
        caption_str = ""
        if caption:
            caption_list = caption if isinstance(caption, list) else [caption]
            caption_style = self.caption_style.build_ass_style()
            caption_str = self._subtitles_to_ass(caption_list, self.start, self.caption_style)

        return "\n".join([
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {self.width}",
            f"PlayResY: {self.height + padding}",
            "",
            self.subtitle_style.build_ass_style_header(),
            sub_style,
            caption_style,
            "",
            event_header,
            sub_str,
            caption_str
        ])


    def build_clip_filters(self, tmp_dir: TemporaryDirectory, subtitles: list[Subtitle] = None, caption: Subtitle = None) -> list[str]:
        vf_filters = []

        if self.boomerang:
            vf_filters.append("[0]reverse[r];[0][r]concat=n=2:v=1:a=0")

            # duplicate and time-shift subtitles so they appear in the reversed half
            if subtitles:
                rev_subs: list[Subtitle] = []
                for sub in subtitles:
                    rel_s = sub.start - self.start
                    rel_e = sub.end - self.start
                    rev_rel_s = 2 * self.duration - rel_e
                    rev_rel_e = 2 * self.duration - rel_s
                    rev_sub = Subtitle(start=self.start + rev_rel_s, end=self.start + rev_rel_e, text=sub.text, delay=sub.delay)
                    rev_subs.append(rev_sub)

                subtitles = subtitles + rev_subs

            if caption:
                caption = Subtitle(
                    start=caption.start,
                    end=caption.end*2,
                    text=caption.text,
                    delay=caption.delay)

        vf_filters.append(f'fps={self.fps}')

        if self.crop:
            vf_filters.append('crop=in_h:in_h')

        vf_filters.append(f'scale={self.width}:{self.height}:flags=lanczos')

        padding = 0
        if caption:
            vf, padding = self.caption_style.build_caption_filters("\\N".join(caption.text), self.width, self.height)
            vf_filters.append(vf)


        ass = self._generate_ass(subtitles, caption, padding)
        ass_file = Path(tmp_dir) / 'sub.ass'
        ass_file.write_text(ass, encoding='utf-8')

        vf_filters.append(f"subtitles={ass_file.resolve()}")

        if self.output_format == VideoFormat.GIF:
            # Palette
            if self.hd_gif:
                vf_filters.append("split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse")
            else:
                vf_filters.append("split[s0][s1];[s0]palettegen=max_colors=32[p];[s1][p]paletteuse=dither=bayer")

        return vf_filters
