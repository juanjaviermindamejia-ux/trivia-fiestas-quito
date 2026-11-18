# Trivia Fiestas de Quito

Trivia con interfaz gráfica sobre las Fiestas de Quito. Las preguntas viven en una base de datos SQLite. Cada vez que el jugador responde mal una pregunta, Python envía una señal por serial a un **ESP32**, que hace clic rápido en un **relé** durante un instante. Si responde bien, no pasa nada.

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
├── scripts/                 # utilidades: listar puertos y probar el relé
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

Si el ESP32 no está conectado, la trivia funciona igual en modo sin relé.

## Configuración

| Qué | Dónde |
|---|---|
| Puerto serial (`serial_port`) y baudios (`baud_rate`) | `src/config.py`, o la variable de entorno `TRIVIA_SERIAL_PORT` |
| Preguntas por partida y aciertos para ganar | `src/config.py` |
| Pin del relé, velocidad de clics, duración y descanso del toque | constantes al inicio de `firmware/esp32_relay/esp32_relay.ino` |

Para saber qué puerto usa tu ESP32 (por defecto se busca `COM3`):

```bash
python -m scripts.list_ports
```

Y para usar ese puerto sin editar código:

```powershell
$env:TRIVIA_SERIAL_PORT = "COM5"      # PowerShell (solo vale para esa terminal)
```
```bash
set TRIVIA_SERIAL_PORT=COM5           # cmd de Windows
export TRIVIA_SERIAL_PORT=/dev/ttyUSB0    # Linux/Mac
```

Para probar el relé sin jugar la trivia (primero **sin la carga conectada**, solo escucha los clics):

```bash
python -m scripts.test_relay
```

## Pruebas

```bash
python -m unittest -v
```

## Agregar preguntas

Las preguntas están agrupadas en `Fiestas de Quito`, `Programación` y `ESPE`.
Edita `sql/seed.sql`: agrega la pregunta con un código nuevo, su categoría y sus 4 opciones,
con solo una `is_correct = 1`. Al abrir la app se insertan solo las nuevas. Para ver la base:
DB Browser for SQLite.

## Hardware

| Módulo relé | ESP32 |
|---|---|
| VCC | 5V (o 3.3V según el módulo) |
| GND | GND |
| IN | GPIO 26 |

Sube `firmware/esp32_relay/esp32_relay.ino` con Arduino IDE. Cierra el Monitor Serial antes de ejecutar Python: el puerto no puede usarse en dos programas a la vez.

**Protocolo serial** (un carácter): `S` inicia un toque (el relé hace clic rápido), `X` lo detiene y apaga el relé. Los tiempos los controla el propio ESP32: el toque siempre termina solo, tiene una duración máxima de 3 s en el firmware y un descanso mínimo entre toques.

**Seguridad:** cablea el relé como normalmente abierto (NO) con una resistencia pull-down en la señal, alimenta el ESP32 con una fuente separada de la carga, y mantén un interruptor de emergencia físico que corte la carga.

## Flujo de trabajo en Git

Todos los integrantes pueden editar todo y subir directo a `main`. Los comandos se ejecutan **dentro de la carpeta del proyecto**:

```bash
git pull                            # 1. traer lo último (siempre primero)
# ...trabajar y probar...
git add .                           # 2. preparar los cambios
git commit -m "feat: descripción"   # 3. guardar con un mensaje claro
git push                            # 4. subir a GitHub
```

- Si `git push` es rechazado, alguien subió antes que tú: ejecuta `git pull` y luego `git push` otra vez.
- Si hay un conflicto, Git marca el archivo con `<<<<<<<`: deja la versión correcta, borra las marcas y repite `git add .`, `git commit` y `git push`.

Prefijos de commit: `feat` (funcionalidad), `fix` (corrección), `docs`, `test`, `refactor`.

## Convenciones de código

- PEP 8, con nombres de variables, funciones y clases en inglés y textos para el usuario en español.
- Type hints en funciones y clases.
- Funciones cortas con una sola tarea; sin números ni textos "mágicos" repetidos (van en `config.py` o en constantes).
- Nada de lógica del juego en `ui/` ni SQL fuera de `database/` y `sql/`.
- Toda lógica nueva lleva su prueba en `tests/`.
