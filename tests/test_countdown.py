import unittest

from src.ui.countdown import Countdown


class CountdownTest(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.timer = Countdown(30, clock=lambda: self.now)

    def test_clock_is_inactive_until_a_lifeline_is_used(self):
        self.assertFalse(self.timer.running)
        self.assertFalse(self.timer.expired)

    def test_deadline_expires_at_thirty_seconds(self):
        self.timer.start()
        self.assertEqual(self.timer.remaining, 30)
        self.now += 29.999
        self.assertEqual(self.timer.remaining, 1)
        self.assertFalse(self.timer.expired)
        self.now = 130.0
        self.assertEqual(self.timer.remaining, 0)
        self.assertTrue(self.timer.expired)

    def test_another_lifeline_does_not_reset_the_deadline(self):
        self.timer.start()
        self.now += 20
        self.timer.start()
        self.assertEqual(self.timer.remaining, 10)

    def test_a_delayed_gui_tick_does_not_grant_extra_time(self):
        self.timer.start()
        self.now += 60
        self.assertTrue(self.timer.expired)
        self.assertEqual(self.timer.remaining, 0)

    def test_cancel_stops_expiration_and_allows_a_new_question(self):
        self.timer.start()
        self.timer.cancel()
        self.now += 60
        self.assertFalse(self.timer.expired)
        self.assertFalse(self.timer.running)
        self.timer.start()
        self.assertEqual(self.timer.remaining, 30)
