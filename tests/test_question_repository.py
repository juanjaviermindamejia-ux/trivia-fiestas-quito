import tempfile
import unittest
from pathlib import Path

from src.config import settings
from src.database.connection import get_connection
from src.database.initializer import initialize_database
from src.database.question_repository import QuestionRepository


class QuestionRepositoryTest(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._temp_dir.name) / "test.db"
        self._initialize()
        self.repository = QuestionRepository(self.db_path)

    def tearDown(self):
        self._temp_dir.cleanup()

    def _initialize(self):
        initialize_database(self.db_path, settings.schema_path, settings.seed_path)

    def test_returns_requested_amount(self):
        self.assertEqual(len(self.repository.get_random_questions(3)), 3)

    def test_every_question_has_exactly_one_correct_option(self):
        for question in self.repository.get_random_questions(100):
            correct = [option for option in question.options if option.is_correct]
            self.assertEqual(len(correct), 1)

    def test_questions_are_grouped_into_the_three_requested_categories(self):
        with get_connection(self.db_path) as connection:
            categories = {
                row["category"]
                for row in connection.execute(
                    "SELECT DISTINCT category FROM questions"
                ).fetchall()
            }
        self.assertEqual(categories, {"Fiestas de Quito", "Programación", "ESPE"})

    def test_initializing_twice_does_not_duplicate_data(self):
        before = len(self.repository.get_random_questions(100))
        self._initialize()
        after = len(self.repository.get_random_questions(100))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
