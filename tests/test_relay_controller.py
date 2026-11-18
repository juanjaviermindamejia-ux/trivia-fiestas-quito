import unittest
from unittest.mock import Mock

from src.hardware.relay_controller import (
    COMMAND_SHOCK,
    COMMAND_STOP,
    NullRelayController,
    SerialRelayController,
)


class SerialRelayControllerTest(unittest.TestCase):
    def setUp(self):
        self.connection = Mock()
        self.relay = SerialRelayController(self.connection, "COM3")

    def test_trigger_sends_shock_command(self):
        self.relay.trigger()
        self.connection.write.assert_called_once_with(COMMAND_SHOCK)

    def test_stop_sends_stop_command(self):
        self.relay.stop()
        self.connection.write.assert_called_once_with(COMMAND_STOP)

    def test_close_stops_relay_and_closes_port(self):
        self.relay.close()
        self.connection.write.assert_called_once_with(COMMAND_STOP)
        self.connection.close.assert_called_once_with()

    def test_write_error_does_not_raise(self):
        self.connection.write.side_effect = OSError("puerto desconectado")
        self.relay.trigger()

    def test_description_includes_port(self):
        self.assertTrue(self.relay.is_connected)
        self.assertIn("COM3", self.relay.description)


class NullRelayControllerTest(unittest.TestCase):
    def test_does_nothing_and_reports_not_connected(self):
        relay = NullRelayController("COM9")
        relay.trigger()
        relay.stop()
        relay.close()
        self.assertFalse(relay.is_connected)
        self.assertIn("COM9", relay.description)


if __name__ == "__main__":
    unittest.main()
