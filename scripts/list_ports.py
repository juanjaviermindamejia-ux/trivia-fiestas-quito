"""Muestra los puertos seriales disponibles para saber cuál es el del ESP32.

Ejecuta desde la raíz del proyecto:  python -m scripts.list_ports
"""
try:
    from serial.tools import list_ports
except ImportError:  # pyserial no instalado
    list_ports = None


def main() -> None:
    if list_ports is None:
        print("Falta pyserial. Instálalo con: pip install -r requirements.txt")
        return
    ports = sorted(list_ports.comports(), key=lambda port: port.device)
    if not ports:
        print("No se encontró ningún puerto. Conecta el ESP32 por USB "
              "(el cable debe ser de datos, no solo de carga).")
        return
    print("Puertos disponibles:")
    for port in ports:
        print(f"  {port.device}  -  {port.description}")
    print("\nEl del ESP32 suele decir CP210x, CH340 o USB Serial. Para usarlo:")
    print('  PowerShell:  $env:TRIVIA_SERIAL_PORT = "COM5"')
    print("  o cambia serial_port en src/config.py")


if __name__ == "__main__":
    main()
