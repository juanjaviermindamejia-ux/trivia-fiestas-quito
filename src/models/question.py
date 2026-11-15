"""Modelos de dominio: no dependen de la base de datos ni de la interfaz."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Option:
    text: str
    is_correct: bool


@dataclass(frozen=True)
class Question:
    id: int
    text: str
    options: tuple[Option, ...]

    def is_correct_option(self, option_index: int) -> bool:
        return self.options[option_index].is_correct
