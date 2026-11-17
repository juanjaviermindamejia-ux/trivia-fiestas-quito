import unittest

from src.models.question import Option, Question
from src.services.game_service import GameService


def build_question(question_id: int) -> Question:
    return Question(
        id=question_id,
        text=f"Pregunta {question_id}",
        options=(Option("Correcta", True), Option("Incorrecta", False)),
    )


class FakeRepository:
    def __init__(self, questions):
        self._questions = questions

    def get_random_questions(self, amount):
        return self._questions[:amount]

    def get_questions_for_game(self):
        return self._questions


class GameServiceTest(unittest.TestCase):
    def setUp(self):
        repository = FakeRepository([build_question(i) for i in range(3)])
        self.game = GameService(repository, questions_per_game=3,
                                correct_answers_to_win=2)
        self.game.start()

    def test_correct_answer_increases_score(self):
        self.assertTrue(self.game.submit_answer(0))
        self.assertEqual(self.game.score, 1)

    def test_wrong_answer_keeps_score(self):
        self.assertFalse(self.game.submit_answer(1))
        self.assertEqual(self.game.score, 0)

    def test_player_wins_with_enough_correct_answers(self):
        self.game.submit_answer(0)
        self.game.advance()
        self.game.submit_answer(0)
        self.game.advance()
        self.game.submit_answer(1)
        self.assertFalse(self.game.advance())

        result = self.game.result()
        self.assertEqual(result.score, 2)
        self.assertTrue(result.won)

    def test_start_without_questions_raises_error(self):
        game = GameService(FakeRepository([]), 3, 2)
        with self.assertRaises(ValueError):
            game.start()

    def test_game_alternates_categories(self):
        questions = [
            Question(i, f"Pregunta {i}", (Option("Correcta", True),),
                     category=category, difficulty=i)
            for i, category in enumerate(
                ["Fiestas de Quito", "Programación", "ESPE"] * 2, start=1
            )
        ]
        game = GameService(FakeRepository(questions), 5, 3)
        game.start()
        categories = [game.current_question.category]
        for _ in range(4):
            game.advance()
            categories.append(game.current_question.category)
        self.assertEqual(
            categories,
            ["Fiestas de Quito", "Programación", "ESPE",
             "Fiestas de Quito", "Programación"],
        )


if __name__ == "__main__":
    unittest.main()
