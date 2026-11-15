# Trivia Fiestas de Quito

Trivia con interfaz gráfica sobre las Fiestas de Quito. Las preguntas viven en una base de datos SQLite. Si el jugador acierta lo suficiente, Python envía una señal por serial a un **ESP32**, que enciende un **relé**.

```
Interfaz (Tkinter) → Servicio (reglas) → Repositorio → SQLite
                          ↓
                  Relé (serial) → ESP32 → Relé
```

## Estructura

```
trivia-fiestas-quito/
├── main.py                  # punto de entrada
├── requirements.txt
├── data/                    # trivia.db se genera aquí (no se sube a Git)
├── sql/
│   ├── schema.sql           # tablas e índices
│   └── seed.sql             # preguntas y opciones iniciales
├── src/
│   ├── config.py            # configuración (puerto, reglas del juego)
│   ├── models/              # clases de dominio (Question, Option)
│   ├── database/            # conexión, inicialización y repositorio
│   ├── services/            # reglas del juego (sin UI ni hardware)
│   ├── hardware/            # comunicación serial con el ESP32
│   └── ui/                  # ventana Tkinter
├── firmware/esp32_relay/    # código Arduino del ESP32
└── tests/                   # pruebas automáticas
```

Cada carpeta tiene una sola responsabilidad: la interfaz no toca SQL y la base de datos no sabe nada de la interfaz.

## Instalación y uso

Requiere Python 3.9 o superior (Tkinter viene incluido; en Linux: `sudo apt install python3-tk`).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
python main.py
```

Puerto del ESP32 (por defecto `COM3`), sin editar código:

```bash
set TRIVIA_SERIAL_PORT=COM5          # Windows
export TRIVIA_SERIAL_PORT=/dev/ttyUSB0   # Linux/Mac
```

Si el ESP32 no está conectado, la trivia funciona igual en modo sin relé.

## Pruebas

```bash
python -m unittest -v
```

## Agregar preguntas

Edita `sql/seed.sql`: agrega la pregunta con un código nuevo (`FQ-009`, `FQ-010`...) y sus 4 opciones, con solo una `is_correct = 1`. Al abrir la app se insertan solo las nuevas. Para ver la base: DB Browser for SQLite.

## Hardware

| Módulo relé | ESP32 |
|---|---|
| VCC | 5V (o 3.3V según el módulo) |
| GND | GND |
| IN | GPIO 26 |

Sube `firmware/esp32_relay/esp32_relay.ino` con Arduino IDE. Cierra el Monitor Serial antes de ejecutar Python: el puerto no puede usarse en dos programas a la vez.

## Flujo de trabajo en Git

Nadie trabaja directo en `main`:

```bash
git pull                                   # traer lo último
git checkout -b feature/nombre-tarea       # rama nueva
# ...trabajar...
git add .
git commit -m "feat: descripción corta"
git push -u origin feature/nombre-tarea
```

Luego abre un **Pull Request** en GitHub, un compañero lo revisa y se hace *merge* a `main`.

Prefijos de commit: `feat` (funcionalidad), `fix` (corrección), `docs`, `test`, `refactor`.

## Convenciones de código

- PEP 8, con nombres de variables, funciones y clases en inglés y textos para el usuario en español.
- Type hints en funciones y clases.
- Funciones cortas con una sola tarea; sin números ni textos "mágicos" repetidos (van en `config.py` o en constantes).
- Nada de lógica del juego en `ui/` ni SQL fuera de `database/` y `sql/`.
- Toda lógica nueva lleva su prueba en `tests/`.
