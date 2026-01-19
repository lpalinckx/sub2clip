from dataclasses import (dataclass, field)

@dataclass(frozen=True, order=True)
class Subtitle:
    """Class to represent a Subtitle. Immutable, and are comparable (by timestamp)

    Properties:
        start (int): start time of the subtitle in milliseconds
        end (int): end time of the subtitle in milliseconds
        text (list[str]): List of lines for this subtitle
        delay (int): delay to add to the original start time, in milliseconds
    """
    start: int # ms
    end: int   # ms
    text: list[str] = field(compare=False)
    delay: int = field(default=0, compare=False)

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

    @property
    def delay_s(self) -> float:
        return self.delay / 1000.0