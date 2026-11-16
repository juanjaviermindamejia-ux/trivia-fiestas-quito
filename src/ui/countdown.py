"""Reloj monotónico de presentación; no depende del ritmo de repintado de Tk."""

from math import ceil
from time import monotonic
from typing import Callable, Optional


class Countdown:
    def __init__(self, seconds: int, clock: Callable[[], float] = monotonic) -> None:
        self._seconds = seconds
        self._clock = clock
        self._deadline: Optional[float] = None

    @property
    def running(self) -> bool:
        return self._deadline is not None

    @property
    def remaining(self) -> int:
        if self._deadline is None:
            return 0
        return max(0, ceil(self._deadline - self._clock()))

    @property
    def expired(self) -> bool:
        return self.running and self.remaining == 0

    def start(self) -> None:
        # Otro comodín comparte el plazo de esta pregunta, sin regalar más tiempo.
        if self._deadline is None:
            self._deadline = self._clock() + self._seconds

    def cancel(self) -> None:
        self._deadline = None
