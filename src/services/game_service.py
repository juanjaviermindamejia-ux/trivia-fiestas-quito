"""Reglas del juego. No conoce la interfaz gráfica ni el hardware."""
from dataclasses import dataclass
from random import sample

from src.database.question_repository import QuestionRepository
from src.models.question import Question


@dataclass(frozen=True)
class GameResult:
    score: int
    total: int
    won: bool
    timed_out: bool = False


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
        self._categories: list[str] = []
        self._current_index = 0
        self._score = 0
        self._timed_out = False
        self._eliminated_options: tuple[int, ...] = ()

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
        return self._questions_per_game if self._categories else len(self._questions)

    @property
    def score(self) -> int:
        return self._score

    @property
    def eliminated_options(self) -> tuple[int, ...]:
        return self._eliminated_options

    @property
    def can_use_fifty_fifty(self) -> bool:
        return (
            bool(self._questions)
            and not self._timed_out
            and not self._eliminated_options
            and sum(not option.is_correct for option in self.current_question.options) >= 2
        )

    def use_fifty_fifty(self) -> tuple[int, ...]:
        """Quita dos opciones incorrectas conservando sus índices originales."""
        if self._timed_out:
            raise ValueError("La partida terminó por tiempo agotado.")
        if self._eliminated_options:
            return self._eliminated_options
        if not self.can_use_fifty_fifty:
            raise ValueError("50:50 necesita al menos dos opciones incorrectas.")
        incorrect = [
            index for index, option in enumerate(self.current_question.options)
            if not option.is_correct
        ]
        self._eliminated_options = tuple(sorted(sample(incorrect, 2)))
        return self._eliminated_options

    def expire_question(self) -> None:
        """No responder dentro del plazo termina la partida en derrota."""
        if self._questions:
            self._timed_out = True

    def start(self) -> None:
        """Inicia la partida; registra solo la primera pregunta efectivamente mostrada."""
        self._questions = []
        self._current_index = 0
        self._score = 0
        self._timed_out = False
        self._eliminated_options = ()
        # Repositorios reales: extraer una pregunta al mostrarla permite guardar
        # el progreso incluso si se abandona una partida antes de terminarla.
        if hasattr(self._repository, "draw_question"):
            self._categories = self._repository.get_categories()
            question = self._draw_next_question(0)
            if question is None:
                raise ValueError("No hay preguntas disponibles en los bancos.")
            self._questions = [question]
        else:
            # Compatibilidad con repositorios simulados en pruebas existentes.
            self._categories = []
            self._questions = self._select_game_questions(
                self._repository.get_questions_for_game()
            )
            if not self._questions:
                raise ValueError("No hay preguntas en la base de datos.")

    def _draw_next_question(self, index: int) -> Question | None:
        """Alterna categorías y comprueba que el ID no está en esta partida."""
        if not self._categories:
            return None
        selected_ids = {q.id for q in self._questions}
        for offset in range(len(self._categories)):
            category = self._categories[(index + offset) % len(self._categories)]
            question = self._repository.draw_question(category, selected_ids)
            if question is not None:
                if question.id in selected_ids:
                    raise ValueError("Se intentó repetir una pregunta en la misma partida")
                return question
        return None

    def _select_game_questions(self, questions: list[Question]) -> list[Question]:
        categories = []
        for question in questions:
            if question.category not in categories:
                categories.append(question.category)
        if len(categories) < 2:
            return questions[:self._questions_per_game]

        selected: list[Question] = []
        unused = list(questions)
        for index in range(self._questions_per_game):
            category = categories[index % len(categories)]
            candidates = [q for q in unused if q.category == category]
            if not candidates:
                continue
            target_difficulty = min(index + 1, 5)
            question = min(
                candidates,
                key=lambda q: (abs(q.difficulty - target_difficulty), q.difficulty),
            )
            selected.append(question)
            unused.remove(question)
        return selected

    def submit_answer(self, option_index: int) -> bool:
        if self._timed_out:
            raise ValueError("La partida terminó por tiempo agotado.")
        if option_index in self._eliminated_options:
            raise ValueError("Esta opción fue eliminada por el comodín 50:50.")
        is_correct = self.current_question.is_correct_option(option_index)
        if is_correct:
            self._score += 1
        return is_correct

    def advance(self) -> bool:
        """Pasa a la siguiente pregunta. Devuelve False si ya no hay más."""
        if self._timed_out or self._current_index + 1 >= self.total_questions:
            return False
        if self._categories:
            question = self._draw_next_question(self._current_index + 1)
            if question is None:
                return False
            self._questions.append(question)
        elif self._current_index + 1 >= len(self._questions):
            return False
        self._current_index += 1
        self._eliminated_options = ()
        return True

    def result(self) -> GameResult:
        return GameResult(
            score=self._score,
            total=self.total_questions,
            won=not self._timed_out and self._score >= self._correct_answers_to_win,
            timed_out=self._timed_out,
        )
