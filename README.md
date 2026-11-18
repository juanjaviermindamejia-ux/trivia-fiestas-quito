# Trivia: Fiestas de Quito, Programación y ESPE

Trivia con interfaz gráfica y tres bancos independientes (50 preguntas de Fiestas de Quito, 50 de Programación y TICs, y 50 de la ESPE). Cada pregunta tiene cuatro opciones y una sola respuesta correcta. Las preguntas y el historial de uso viven en una base de datos SQLite. Cada vez que el jugador responde mal una pregunta, Python envía una señal por serial a un **ESP32**, que hace clic rápido en un **relé** durante un instante. Si responde bien, no pasa nada.

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
├── banks/                   # los 3 archivos TXT originales
├── data/                    # trivia.db (incluida, se sincroniza al abrir)
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
├── scripts/                 # importador TXT, puertos y pruebas del relé
└── tests/                   # pruebas automáticas
```

Cada carpeta tiene una sola responsabilidad: la interfaz no toca SQL y la base de datos no sabe nada de la interfaz.

## Instalación y uso

Requiere Python 3.10 o superior (Tkinter viene incluido; en Linux: `sudo apt install python3-tk`).

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

Para saber qué puerto usa tu ESP32 (por defecto se configura `COM6`):

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

## Bancos de preguntas y control de repetición

| Archivo TXT | Categoría en SQLite | Códigos | Preguntas |
|---|---|---|---:|
| `banks/fiestas_de_quito.txt` | Fiestas de Quito | `FQ-001` a `FQ-050` | 50 |
| `banks/programacion.txt` | Programación | `PG-001` a `PG-050` | 50 |
| `banks/espe.txt` | ESPE | `ES-001` a `ES-050` | 50 |

Las opciones A, B, C y D están en la tabla `options`, con exactamente una marcada como correcta.
La tabla `used_questions` guarda los identificadores ya mostrados y funciona como historial
independiente para cada categoría. Este historial **permanece después de cerrar la app**.

### ¿Cómo se evitan las repeticiones?

1. Al mostrar una pregunta, el programa carga en un conjunto los IDs usados de esa categoría.
2. Escoge aleatoriamente una pregunta cuyo ID no esté en ese conjunto **ni en la partida actual**.
3. Verifica que existan cuatro opciones y una sola correcta, y guarda el ID en SQLite.
4. Cuando un banco ha mostrado sus 50 preguntas, **solo su historial se vacía** en la siguiente extracción; inicia otro ciclo aleatorio.
5. Los otros dos bancos continúan donde quedaron, sin perder su progreso.

El juego alterna las categorías (Quito → Programación → ESPE), muestra **5 preguntas
por partida** y exige **3 aciertos** para ganar, como en el código original.
Una partida interrumpida solo consume las preguntas que llegaron a mostrarse.

### Cómo actualizar los bancos desde los TXT

Edita las preguntas en `banks/`, manteniendo su numeración, cuatro opciones `A)` a `D)`
y la línea `-> Respuesta correcta: X) ...`. Después ejecuta:

```bash
python -m scripts.import_question_banks
python main.py
```

El primer comando regenera `sql/seed.sql` y valida el contenido, las cuatro opciones y
la respuesta correcta de los 150 registros. `main.py` actualiza SQLite al inicio, sin
borrar el historial de las preguntas que mantienen sus identificadores. Para consultar
la base puedes utilizar DB Browser for SQLite.

Para **reiniciar manualmente todos los ciclos** (solo si deseas empezar desde cero):

```sql
DELETE FROM used_questions;
```

No es necesario ejecutar este comando para el uso normal del juego.

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
