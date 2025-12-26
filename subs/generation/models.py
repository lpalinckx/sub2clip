from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from tempfile import TemporaryDirectory
from typing import Optional

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
    name: str = "subStyle"
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


    def build_drawtext_filters(self, text: list[str], is_caption: bool, tmpdir: TemporaryDirectory) -> list[str]:
        # TODO This still needs to be refactored for captions
        """Returns the drawtext filters with the corresponding text and font settings

        Args:
            text (list[str]): text to display
            is_caption (bool): Determines whether to put the text in the caption area or as subtitles. Defaults to False.
            tmpdir (TemporaryDirectory): Temp directory of the system
        """
        vf = []

        lines = list(reversed(text)) if is_caption else text

        padding = (2 + len(text) * self.font_size if is_caption else 0)
        if is_caption:
            vf.append(f"pad=iw:(ih+{padding}):0:{padding}")

        text_height    = len(text) * font_size
        padding_offset = (padding - text_height)/2

        for i, line in enumerate(text, start=1):
            filename = f'caption-{i}.txt' if is_caption else f'subtitle-{i}.txt'
            # Writing the line to a file helps circumvent ffmpeg's weird escaping rules ¯\_(ツ)_/¯
            # https://ffmpeg.org/ffmpeg-filters.html#Notes-on-filtergraph-escaping
            text_file = Path(tmp) / filename

            with open(text_file, 'w', encoding='utf-8') as file:
                file.write(line)

            fontfile_str = f"fontfile='{self.font.resolve()}':" if self.font else ''
            text_file    = text_file.resolve()

            x = "10" if is_caption else "(w-text_w)/2"
            y = f"{padding_offset} + {i}*line_h - line_h" if is_caption else f"(h-{i}*line_h)"

            vf.append(
                f"drawtext=textfile='{text_file}':"
                f"{fontfile_str}"
                f"fontcolor={self.font_color}:"
                f"fontsize={self.font_size}:"
                f"x={x}:y={y}:"
                f"bordercolor={self.border_color}:borderw={self.border_width}"
            )
        return vf

@dataclass
class ClipSettings:
    input_path: Path
    clip_path: Path
    output_path: Path
    output_format: VideoFormat
    text_style: TextStyle
    start: int
    end: int
    fps: int = 20
    width: Optional[int] = None
    height: Optional[int] = None
    resolution: Optional[int] = None
    crop: bool = False
    boomerang: bool = False
    hd_gif: bool = False
    mp4_copy: bool = False
    # Compression settings for FFmpeg
    crf: int = 18
    preset: str = "medium"

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

        ## Check if the filetype set in the filename is the same as the output_format
        parts = self.output_path.split('.')
        if len(parts) > 1:
            if VideoFormat[parts[1].upper()] != self.output_format:
                raise ValueError(f"Output filename had set filetype as '{parts[1]}', but given output_format was {self.output_format}")

        ## Check if self.crop is set and validate the width/height
        if self.crop and not res_set:
            if self.width != self.height:
                raise ValueError("Crop was set to true, but width doesn't match height")


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

    def build_clip_filters(self, sub_file: Path = None, vf_caption: list[str] = None) -> list[str]:
        vf_filters = []

        if self.boomerang:
            vf_filters.append("[0]reverse[r];[0][r]concat=n=2:v=1:a=0")

        vf_filters.append(f'fps={self.fps}')

        if self.crop:
            vf_filters.append('crop=in_h:in_h')

        if self.resolution:
            vf_filters.append(f'scale=-1:{self.resolution}:flags=lanczos')
        else:
            vf_filters.append(f'scale={self.width}:{self.height}:flags=lanczos')

        if sub_file:
            vf_filters.append(f"subtitles={sub_file.resolve()}")

        # TODO
        # if vf_caption:
        #     vf_filters.append(vf_caption)

        if self.output_format == VideoFormat.GIF:
            # Palette
            if self.hd_gif:
                vf_filters.append("split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse")
            else:
                vf_filters.append("split[s0][s1];[s0]palettegen=max_colors=32[p];[s1][p]paletteuse=dither=bayer")

        return vf_filters
