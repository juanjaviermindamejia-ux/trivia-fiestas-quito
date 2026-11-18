"""Control del relé a través del ESP32 por puerto serial.

Protocolo (un solo carácter):
  b"S" -> el ESP32 inicia un toque (clics rápidos del relé) y él mismo lo termina
  b"X" -> el ESP32 detiene el toque y apaga el relé

Velocidad de clics, duración y descanso se configuran en el firmware:
firmware/esp32_relay/esp32_relay.ino
"""
import logging
import time
from typing import Protocol

try:
    import serial
except ImportError:  # pyserial no instalado
    serial = None

logger = logging.getLogger(__name__)

COMMAND_SHOCK = b"S"
COMMAND_STOP = b"X"
ESP32_BOOT_SECONDS = 2  # el ESP32 se reinicia al abrir el puerto


class RelayController(Protocol):
    is_connected: bool

    @property
    def description(self) -> str: ...

    def trigger(self) -> None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...


class NullRelayController:
    """Sustituto sin hardware: permite usar la trivia sin el ESP32."""

    is_connected = False

    def __init__(self, port: str = "") -> None:
        self._port = port

    @property
    def description(self) -> str:
        suffix = f" ({self._port})" if self._port else ""
        return f"Modo sin relé · ESP32 no conectado{suffix}"

    def trigger(self) -> None:
        logger.info("Toque (simulado)")

    def stop(self) -> None:
        logger.info("Stop (simulado)")

    def close(self) -> None:
        pass


class SerialRelayController:
    is_connected = True

    def __init__(self, connection: "serial.Serial", port: str) -> None:
        self._connection = connection
        self._port = port

    @property
    def description(self) -> str:
        return f"ESP32 conectado · {self._port}"

    def trigger(self) -> None:
        self._send(COMMAND_SHOCK)

    def stop(self) -> None:
        self._send(COMMAND_STOP)

    def close(self) -> None:
        self.stop()
        self._connection.close()

    def _send(self, command: bytes) -> None:
        try:
            self._connection.write(command)
        except OSError as error:  # serial.SerialException hereda de OSError
            logger.error("No se pudo enviar al ESP32: %s", error)


def create_relay_controller(port: str, baud_rate: int) -> RelayController:
    """Devuelve el controlador real si el ESP32 responde; si no, uno simulado."""
    if serial is None:
        logger.warning("pyserial no está instalado: modo sin relé")
        return NullRelayController(port)
    try:
        connection = serial.Serial(port, baud_rate, timeout=1)
    except serial.SerialException as error:
        logger.warning("No se pudo abrir %s (%s): modo sin relé", port, error)
        return NullRelayController(port)
    time.sleep(ESP32_BOOT_SECONDS)
    return SerialRelayController(connection, port)
