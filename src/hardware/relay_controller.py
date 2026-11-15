"""Control del relé a través del ESP32 por puerto serial.

Protocolo: se envía b"1" para encender y b"0" para apagar.
"""
import logging
import time
from typing import Protocol

try:
    import serial
except ImportError:  # pyserial no instalado
    serial = None

logger = logging.getLogger(__name__)

COMMAND_ON = b"1"
COMMAND_OFF = b"0"
ESP32_BOOT_SECONDS = 2  # el ESP32 se reinicia al abrir el puerto


class RelayController(Protocol):
    is_connected: bool

    def turn_on(self) -> None: ...
    def turn_off(self) -> None: ...
    def close(self) -> None: ...


class NullRelayController:
    """Sustituto sin hardware: permite usar la trivia sin el ESP32."""

    is_connected = False

    def turn_on(self) -> None:
        logger.info("Relé ON (simulado)")

    def turn_off(self) -> None:
        logger.info("Relé OFF (simulado)")

    def close(self) -> None:
        pass


class SerialRelayController:
    is_connected = True

    def __init__(self, connection: "serial.Serial") -> None:
        self._connection = connection

    def turn_on(self) -> None:
        self._send(COMMAND_ON)

    def turn_off(self) -> None:
        self._send(COMMAND_OFF)

    def close(self) -> None:
        self.turn_off()
        self._connection.close()

    def _send(self, command: bytes) -> None:
        try:
            self._connection.write(command)
        except serial.SerialException as error:
            logger.error("No se pudo enviar al ESP32: %s", error)


def create_relay_controller(port: str, baud_rate: int) -> RelayController:
    """Devuelve el controlador real si el ESP32 responde; si no, uno simulado."""
    if serial is None:
        logger.warning("pyserial no está instalado: modo sin relé")
        return NullRelayController()
    try:
        connection = serial.Serial(port, baud_rate, timeout=1)
    except serial.SerialException as error:
        logger.warning("No se pudo abrir %s (%s): modo sin relé", port, error)
        return NullRelayController()
    time.sleep(ESP32_BOOT_SECONDS)
    return SerialRelayController(connection)
