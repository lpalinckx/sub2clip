from dataclasses import (dataclass, field)

# Subtitle class
@dataclass(frozen=True, order=True)
class Subtitle:
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