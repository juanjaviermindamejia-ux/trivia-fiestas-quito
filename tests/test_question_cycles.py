"""Verifica bancos de 50 preguntas, ciclos independientes y progreso persistente."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.config import settings
from src.database.connection import get_connection
from src.database.initializer import initialize_database
from src.database.question_repository import QuestionRepository
from src.services.game_service import GameService


class QuestionCycleTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.db = Path(self.temporary.name) / "questions.db"
        initialize_database(self.db, settings.schema_path, settings.seed_path)
        self.repo = QuestionRepository(self.db)

    def used_count(self, category):
        with get_connection(self.db) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM used_questions WHERE category = ?", (category,)
            ).fetchone()[0]

    def test_three_banks_each_have_fifty_questions_and_four_options(self):
        with get_connection(self.db) as conn:
            rows = conn.execute(
                "SELECT q.category, COUNT(DISTINCT q.id) AS questions, "
                "COUNT(o.id) AS options, SUM(o.is_correct) AS correct "
                "FROM questions q JOIN options o ON o.question_id = q.id "
                "GROUP BY q.category"
            ).fetchall()
        self.assertEqual(
            {r["category"]: (r["questions"], r["options"], r["correct"]) for r in rows},
            {"Fiestas de Quito": (50, 200, 50),
             "Programación": (50, 200, 50),
             "ESPE": (50, 200, 50)},
        )
        self.assertTrue(all(len(q.options) == 4 for q in self.repo.get_random_questions(150)))

    def test_no_repeats_until_category_exhausts_then_starts_new_cycle(self):
        for category in self.repo.get_categories():
            first_round = [self.repo.draw_question(category).id for _ in range(50)]
            self.assertEqual(len(set(first_round)), 50, category)
            self.assertEqual(self.used_count(category), 50)
            next_question = self.repo.draw_question(category)
            self.assertIn(next_question.id, first_round)
            self.assertEqual(self.used_count(category), 1)

    def test_finishing_one_category_does_not_reset_other_banks(self):
        self.repo.draw_question("Programación")
        self.repo.draw_question("ESPE")
        for _ in range(51):
            self.repo.draw_question("Fiestas de Quito")
        self.assertEqual(self.used_count("Fiestas de Quito"), 1)
        self.assertEqual(self.used_count("Programación"), 1)
        self.assertEqual(self.used_count("ESPE"), 1)

    def test_history_survives_application_restart_and_reimport(self):
        first_question = self.repo.draw_question("ESPE")
        self.assertEqual(self.used_count("ESPE"), 1)
        initialize_database(self.db, settings.schema_path, settings.seed_path)
        reopened = QuestionRepository(self.db)
        self.assertNotEqual(reopened.draw_question("ESPE").id, first_question.id)
        self.assertEqual(self.used_count("ESPE"), 2)

    def test_questions_are_marked_only_when_displayed(self):
        game = GameService(self.repo, 5, 3)
        game.start()
        self.assertEqual(sum(self.used_count(c) for c in self.repo.get_categories()), 1)
        seen = [game.current_question.id]
        for _ in range(4):
            self.assertTrue(game.advance())
            seen.append(game.current_question.id)
        self.assertEqual(len(set(seen)), 5)
        self.assertEqual(sum(self.used_count(c) for c in self.repo.get_categories()), 5)
        self.assertFalse(game.advance())
        self.assertEqual(game.total_questions, 5)
        self.assertEqual(game.result().total, 5)

    def test_two_games_do_not_repeat_questions(self):
        game = GameService(self.repo, 5, 3)
        ids = []
        for _ in range(2):
            game.start()
            ids.append(game.current_question.id)
            for _ in range(4):
                self.assertTrue(game.advance())
                ids.append(game.current_question.id)
        self.assertEqual(len(ids), len(set(ids)))

    def test_boundary_between_cycles_does_not_repeat_in_same_game(self):
        # Deja solo una pregunta inédita en el banco. La última puede
        # seleccionarse al inicio y en la siguiente extracción comienza un ciclo nuevo.
        for _ in range(49):
            self.repo.draw_question("Fiestas de Quito")
        last = self.repo.draw_question("Fiestas de Quito")
        following = self.repo.draw_question("Fiestas de Quito", {last.id})
        self.assertNotEqual(following.id, last.id)
        self.assertEqual(self.used_count("Fiestas de Quito"), 1)

    def test_old_sqlite_schema_can_be_migrated(self):
        old_path = Path(self.temporary.name) / "old.db"
        with sqlite3.connect(old_path) as conn:
            conn.executescript(
                "CREATE TABLE questions (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "code TEXT NOT NULL UNIQUE, text TEXT NOT NULL, category TEXT NOT NULL);"
                "CREATE TABLE options (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE, "
                "text TEXT NOT NULL, is_correct INTEGER NOT NULL, "
                "UNIQUE(question_id, text));"
                "INSERT INTO questions(code,text,category) "
                "VALUES ('FQ-001','Versión antigua','Fiestas de Quito');"
            )
        initialize_database(old_path, settings.schema_path, settings.seed_path)
        with sqlite3.connect(old_path) as conn:
            cols = [row[1] for row in conn.execute("PRAGMA table_info(questions)")]
            self.assertIn("difficulty", cols)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0], 150)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM options").fetchone()[0], 600)


if __name__ == "__main__":
    unittest.main()
