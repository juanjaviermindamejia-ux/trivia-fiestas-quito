"""Prueba manual del relé sin jugar la trivia.

Úsala primero SIN la carga conectada: solo debes oír los clics del relé.
Ejecuta desde la raíz del proyecto:  python -m scripts.test_relay
"""
from src.config import settings
from src.hardware.relay_controller import create_relay_controller


def main() -> None:
    relay = create_relay_controller(settings.serial_port, settings.baud_rate)
    print(relay.description)
    if not relay.is_connected:
        print("Sin conexión con el ESP32. Revisa el puerto con: "
              "python -m scripts.list_ports")
        return

    print("Enter = enviar un toque de prueba | x + Enter = detener | q + Enter = salir")
    try:
        while True:
            entry = input("> ").strip().lower()
            if entry == "q":
                break
            if entry == "x":
                relay.stop()
            else:
                relay.trigger()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        relay.close()


if __name__ == "__main__":
    main()
