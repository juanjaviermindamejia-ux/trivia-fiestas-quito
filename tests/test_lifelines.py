"""Reglas de comodines verificadas con las preguntas originales de SQLite."""

import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.config import settings
from src.database.initializer import initialize_database
from src.database.question_repository import QuestionRepository
from src.hardware.relay_controller import NullRelayController
from src.services.game_service import GameService
from src.ui.countdown import Countdown
from src.ui.main_window import MainWindow


class DatabaseGameTestCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        db_path = Path(temporary.name) / "trivia.db"
        initialize_database(db_path, settings.schema_path, settings.seed_path)
        self.game = GameService(QuestionRepository(db_path), 5, 3)
        self.game.start()

    def correct_index(self):
        return next(index for index, option in enumerate(self.game.current_question.options)
                    if option.is_correct)

    def wrong_index(self):
        return next(index for index, option in enumerate(self.game.current_question.options)
                    if not option.is_correct)


class GameLifelineTest(DatabaseGameTestCase):
    def test_fifty_fifty_eliminates_exactly_two_incorrect_options(self):
        original = self.game.current_question
        eliminated = self.game.use_fifty_fifty()
        self.assertEqual(len(set(eliminated)), 2)
        self.assertTrue(all(not original.options[i].is_correct for i in eliminated))
        self.assertNotIn(self.correct_index(), eliminated)
        self.assertIs(self.game.current_question, original)
        self.assertEqual(self.game.score, 0)

    def test_fifty_fifty_cannot_reroll_or_submit_a_removed_option(self):
        eliminated = self.game.use_fifty_fifty()
        self.assertEqual(self.game.use_fifty_fifty(), eliminated)
        with self.assertRaises(ValueError):
            self.game.submit_answer(eliminated[0])
        self.assertEqual(self.game.score, 0)
        self.assertTrue(self.game.submit_answer(self.correct_index()))

    def test_next_question_restores_all_original_options(self):
        self.game.use_fifty_fifty()
        self.game.submit_answer(self.correct_index())
        self.assertTrue(self.game.advance())
        self.assertEqual(self.game.eliminated_options, ())
        self.assertTrue(self.game.can_use_fifty_fifty)

    def test_timeout_loses_even_after_reaching_the_score_threshold(self):
        for _ in range(3):
            self.game.submit_answer(self.correct_index())
            self.game.advance()
        self.game.expire_question()
        result = self.game.result()
        self.assertEqual(result.score, 3)
        self.assertTrue(result.timed_out)
        self.assertFalse(result.won)

    def test_timeout_blocks_answer_lifeline_and_advancement(self):
        self.game.expire_question()
        self.game.expire_question()
        with self.assertRaises(ValueError):
            self.game.submit_answer(self.correct_index())
        with self.assertRaises(ValueError):
            self.game.use_fifty_fifty()
        self.assertFalse(self.game.advance())
        self.assertEqual(self.game.current_number, 1)
        self.assertEqual(self.game.score, 0)

    def test_restart_clears_timeout_and_eliminated_options(self):
        self.game.use_fifty_fifty()
        self.game.expire_question()
        self.game.start()
        self.assertFalse(self.game.result().timed_out)
        self.assertEqual(self.game.eliminated_options, ())
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.current_number, 1)


class LifelineUITest(DatabaseGameTestCase):
    def setUp(self):
        super().setUp()
        self.now = 0.0
        self.relay = Mock(spec=NullRelayController)
        self.relay.is_connected = False
        self.relay.description = "Modo sin relé"
        try:
            self.app = MainWindow(self.game, self.relay)
        except tk.TclError as error:
            self.skipTest(f"La prueba gráfica requiere una pantalla Tk: {error}")
        self.addCleanup(self.app._on_close)
        self.app.withdraw()
        self.app._countdown = Countdown(30, clock=lambda: self.now)
        self.errors = []
        self.app.report_callback_exception = lambda *error: self.errors.append(error)
        self.app._start_game()
        self.app.update_idletasks()

    def tearDown(self):
        self.assertEqual(self.errors, [])

    def next_question(self):
        self.app.after_cancel(self.app._next_job)
        self.app._go_next()
        self.app.update_idletasks()

    def test_all_three_controls_start_a_thirty_second_countdown(self):
        for index in range(3):
            with self.subTest(lifeline=index):
                self.app._start_game()
                self.app.update_idletasks()
                self.app._lifeline_items[index].button.invoke()
                self.assertEqual(self.app._countdown.remaining, 30)
                self.assertIn("00:30", self.app._timer_label.cget("text"))
                self.assertEqual(self.game.score, 0)

    def test_fifty_fifty_hides_two_options_and_preserves_original_letters(self):
        self.app._lifeline_items[1].button.invoke()
        removed = self.game.eliminated_options
        self.assertEqual(sum(bool(b.grid_info()) for b in self.app._option_buttons), 2)
        for index, button in enumerate(self.app._option_buttons):
            self.assertTrue(button.button.cget("text").startswith(f"{chr(65 + index)}:"))
            if index in removed:
                self.assertEqual(str(button.button.cget("state")), "disabled")
                self.app._on_answer(index)
        self.assertEqual(self.game.score, 0)
        self.assertFalse(self.app._answer_pending)

    def test_combining_lifelines_does_not_extend_time(self):
        self.app._activate_lifeline(0)
        self.now = 20
        self.app._activate_lifeline(2)
        self.app._activate_lifeline(1)
        self.assertEqual(self.app._countdown.remaining, 10)
        self.assertEqual(self.app._lifeline_used, {0, 1, 2})

    def test_answer_before_deadline_cancels_timeout_and_next_question_resets(self):
        self.app._activate_lifeline(1)
        self.now = 29.99
        self.app._on_answer(self.correct_index())
        self.assertFalse(self.app._countdown.running)
        self.assertIsNone(self.app._timer_job)
        self.assertEqual(self.game.score, 1)
        self.now = 60
        self.app._tick_countdown()
        self.assertFalse(self.game.result().timed_out)
        self.next_question()
        self.assertFalse(self.app._countdown.running)
        self.assertEqual(self.app._lifeline_used, set())
        self.assertEqual(sum(bool(b.grid_info()) for b in self.app._option_buttons), 4)

    def test_a_click_at_the_deadline_loses_before_the_gui_tick(self):
        self.app._activate_lifeline(0)
        self.now = 30
        self.app._on_answer(self.correct_index())
        self.assertTrue(self.game.result().timed_out)
        self.assertFalse(self.game.result().won)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.app._screen, "result")
        self.assertIn("Perdiste", self.app._question_label.cget("text"))
        self.relay.trigger.assert_not_called()
        self.app._play_button.button.invoke()
        self.app.update_idletasks()
        self.assertFalse(self.game.result().timed_out)
        self.assertIsNone(self.app._timer_job)

    def test_wrong_answer_triggers_relay_once(self):
        self.app._on_answer(self.wrong_index())
        self.relay.trigger.assert_called_once_with()

    def test_correct_answer_does_not_trigger_relay(self):
        self.app._on_answer(self.correct_index())
        self.relay.trigger.assert_not_called()

    def test_tick_expires_game_without_relay_even_with_three_correct_answers(self):
        for _ in range(3):
            self.app._on_answer(self.correct_index())
            self.next_question()
        self.app._activate_lifeline(2)
        self.now = 30
        self.app.after_cancel(self.app._timer_job)
        self.app._tick_countdown()
        self.assertFalse(self.game.result().won)
        self.assertTrue(self.game.result().timed_out)
        self.assertIn("00:00", self.app._timer_label.cget("text"))
        self.relay.trigger.assert_not_called()
