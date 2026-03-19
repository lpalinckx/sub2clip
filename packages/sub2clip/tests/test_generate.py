import sub2clip.sub2clip
from sub2clip.generation.models import ClipSettings, VideoFormat, Subtitle
import pytest
from tempfile import TemporaryDirectory
from pathlib import Path
from returns.pipeline import is_successful

def test_generate_thumbnail():

    with TemporaryDirectory(delete=True) as tmp:
        clip_settings = ClipSettings(
            input_path=Path("packages/sub2clip/tests/samples/sample.mp4").absolute(),
            output_path=Path(f"{tmp}/thumbnail.jpg"),
            output_format=VideoFormat.JPG,
            resolution=200,
            start=5000,
            end=5000,
        )

        err = sub2clip.sub2clip.generate(
            clip_settings=clip_settings,
            subtitles=[Subtitle(text="This is a test", start=5000, end=5001)],
            thumbnail=True,
        )

        assert is_successful(err)