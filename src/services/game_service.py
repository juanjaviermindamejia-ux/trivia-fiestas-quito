"""Reglas del juego. No conoce la interfaz gráfica ni el hardware."""
from dataclasses import dataclass

from src.database.question_repository import QuestionRepository
from src.models.question import Question


@dataclass(frozen=True)
class GameResult:
    score: int
    total: int
    won: bool


class GameService:
    def __init__(
        self,
        repository: QuestionRepository,
        questions_per_game: int,
        correct_answers_to_win: int,
    ) -> None:
        self._repository = repository
        self._questions_per_game = questions_per_game
        self._correct_answers_to_win = correct_answers_to_win
        self._questions: list[Question] = []
        self._current_index = 0
        self._score = 0

    @property
    def questions_per_game(self) -> int:
        return self._questions_per_game

    @property
    def correct_answers_to_win(self) -> int:
        return self._correct_answers_to_win

    @property
    def current_question(self) -> Question:
        return self._questions[self._current_index]

    @property
    def current_number(self) -> int:
        return self._current_index + 1

    @property
    def total_questions(self) -> int:
        return len(self._questions)

    @property
    def score(self) -> int:
        return self._score

    def start(self) -> None:
        questions = self._repository.get_random_questions(self._questions_per_game)
        if not questions:
            raise ValueError("No hay preguntas en la base de datos.")
        self._questions = questions
        self._current_index = 0
        self._score = 0

    def submit_answer(self, option_index: int) -> bool:
        is_correct = self.current_question.is_correct_option(option_index)
        if is_correct:
            self._score += 1
        return is_correct

    def advance(self) -> bool:
        """Pasa a la siguiente pregunta. Devuelve False si ya no hay más."""
        if self._current_index + 1 >= len(self._questions):
            return False
        self._current_index += 1
        return True

    def result(self) -> GameResult:
        return GameResult(
            score=self._score,
            total=len(self._questions),
            won=self._score >= self._correct_answers_to_win,
        )
