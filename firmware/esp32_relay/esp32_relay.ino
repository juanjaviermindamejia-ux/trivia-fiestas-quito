// Control del relé para la trivia (ESP32) con panel web de configuración.
//
// Comandos por serial (los envía Python, un carácter):
//   'S'  inicia un toque: el relé hace clic rápido durante la duración configurada
//   'X'  detiene todo y apaga el relé de inmediato
//
// Panel web (el ESP32 crea su propia red Wi-Fi; no necesita router ni internet):
//   1. Conéctate a la red AP_SSID con la clave AP_PASSWORD.
//   2. Abre http://192.168.4.1 en el navegador.
//   3. Cambia duración, clics por segundo y descanso. Se guardan solos y se
//      conservan al apagar el ESP32.
// Los límites LIMIT_* son fijos en este firmware: el panel nunca puede superarlos.
// El panel NO controla la intensidad: eso depende de la fuente y de la bobina.
//
// Los tiempos los controla el propio ESP32 (no Python): así el toque no depende
// del retardo del USB y siempre termina solo, aunque se desconecte el cable.

#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>

// ---------- Hardware (edita aquí) ----------
const int RELAY_PIN = 26;       // GPIO conectado al IN del módulo de relé
const long BAUD_RATE = 115200;  // debe ser igual a baud_rate en src/config.py

// Muchos módulos de relé son "activo en bajo": si funciona al revés,
// intercambia HIGH y LOW en estas dos líneas.
const int RELAY_ON = HIGH;
const int RELAY_OFF = LOW;

// ---------- Red Wi-Fi del panel (cambia la clave) ----------
const char* AP_SSID = "Trivia-Toque";
const char* AP_PASSWORD = "12345678";  // mínimo 8 caracteres

// ---------- Límites fijos de seguridad (el panel no puede superarlos) ----------
const long LIMIT_DURATION_MIN_MS = 200;
const long LIMIT_DURATION_MAX_MS = 5000;   // un toque nunca dura más de 3 s
const long LIMIT_CLICKS_MIN = 5;
const long LIMIT_CLICKS_MAX = 20;          // un relé mecánico no sigue más rápido
const long LIMIT_COOLDOWN_MIN_MS = 1000;   // descanso mínimo entre toques
const long LIMIT_COOLDOWN_MAX_MS = 10000;

// ---------- Valores iniciales (luego se cambian desde el panel) ----------
const long DEFAULT_DURATION_MS = 1000;
const long DEFAULT_CLICKS_PER_SECOND = 10;
const long DEFAULT_COOLDOWN_MS = 2000;
// -------------------------------------------------

long durationMs = DEFAULT_DURATION_MS;
long clicksPerSecond = DEFAULT_CLICKS_PER_SECOND;
long cooldownMs = DEFAULT_COOLDOWN_MS;

bool burstActive = false;
bool hasFinishedBurst = false;
bool relayIsOn = false;
unsigned long burstStart = 0;
unsigned long lastToggle = 0;
unsigned long lastBurstEnd = 0;

Preferences prefs;
WebServer server(80);

// ---------- Ajustes guardados ----------
long clampTo(long value, long low, long high) {
  if (value < low) return low;
  if (value > high) return high;
  return value;
}

void saveSettings(long duration, long clicks, long cooldown) {
  durationMs = clampTo(duration, LIMIT_DURATION_MIN_MS, LIMIT_DURATION_MAX_MS);
  clicksPerSecond = clampTo(clicks, LIMIT_CLICKS_MIN, LIMIT_CLICKS_MAX);
  cooldownMs = clampTo(cooldown, LIMIT_COOLDOWN_MIN_MS, LIMIT_COOLDOWN_MAX_MS);
  prefs.putUInt("dur", (uint32_t)durationMs);
  prefs.putUInt("clk", (uint32_t)clicksPerSecond);
  prefs.putUInt("cool", (uint32_t)cooldownMs);
}

void loadSettings() {
  prefs.begin("toque", false);
  durationMs = clampTo((long)prefs.getUInt("dur", DEFAULT_DURATION_MS),
                       LIMIT_DURATION_MIN_MS, LIMIT_DURATION_MAX_MS);
  clicksPerSecond = clampTo((long)prefs.getUInt("clk", DEFAULT_CLICKS_PER_SECOND),
                            LIMIT_CLICKS_MIN, LIMIT_CLICKS_MAX);
  cooldownMs = clampTo((long)prefs.getUInt("cool", DEFAULT_COOLDOWN_MS),
                       LIMIT_COOLDOWN_MIN_MS, LIMIT_COOLDOWN_MAX_MS);
}

// ---------- Relé y toque ----------
void setRelay(bool on) {
  digitalWrite(RELAY_PIN, on ? RELAY_ON : RELAY_OFF);
  relayIsOn = on;
}

void startBurst() {
  unsigned long now = millis();
  if (burstActive) return;  // ya hay un toque en curso
  if (hasFinishedBurst && now - lastBurstEnd < (unsigned long)cooldownMs) return;  // en descanso
  burstActive = true;
  burstStart = now;
  lastToggle = now;
  setRelay(true);
}

void stopBurst() {
  if (burstActive) {
    burstActive = false;
    hasFinishedBurst = true;
    lastBurstEnd = millis();
  }
  setRelay(false);
}

void updateBurst() {
  if (!burstActive) return;
  unsigned long now = millis();
  if (now - burstStart >= (unsigned long)durationMs) {
    stopBurst();
    return;
  }
  // Medio ciclo encendido y medio apagado: 1000 / clics = periodo de un clic.
  unsigned long halfPeriodMs = 500UL / (unsigned long)clicksPerSecond;
  if (now - lastToggle >= halfPeriodMs) {
    setRelay(!relayIsOn);
    lastToggle = now;
  }
}

// ---------- Panel web ----------
String formatSeconds(long ms) {
  return String(ms / 1000.0, 1);
}

String buildPage(bool saved) {
  String html = "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>";
  html += "<meta name='viewport' content='width=device-width,initial-scale=1'>";
  html += "<title>Configuración del toque</title><style>";
  html += "body{font-family:Arial,sans-serif;background:#030d25;color:#f6f7ff;margin:0;padding:20px}";
  html += ".card{max-width:420px;margin:auto;background:#071c45;border:2px solid #f8cf56;";
  html += "border-radius:12px;padding:20px}";
  html += "h1{color:#ffe9a0;font-size:22px;margin-top:0}";
  html += "label{display:block;margin-top:16px;font-weight:bold}";
  html += "small{color:#b3c6e6}";
  html += "input{width:100%;box-sizing:border-box;padding:10px;font-size:18px;margin-top:6px;";
  html += "border-radius:6px;border:0}";
  html += "button{width:100%;margin-top:22px;padding:14px;font-size:18px;font-weight:bold;";
  html += "background:#f8cf56;border:0;border-radius:8px}";
  html += ".ok{background:#124936;border-radius:6px;padding:8px;margin-bottom:8px}";
  html += "</style></head><body><div class='card'><h1>Configuración del toque</h1>";
  if (saved) html += "<div class='ok'>Guardado</div>";
  html += "<form method='POST' action='/save'>";

  html += "<label>Duración del toque (segundos)</label>";
  html += "<input type='number' name='duration' step='0.1' min='";
  html += formatSeconds(LIMIT_DURATION_MIN_MS);
  html += "' max='";
  html += formatSeconds(LIMIT_DURATION_MAX_MS);
  html += "' value='";
  html += formatSeconds(durationMs);
  html += "'><small>Permitido: ";
  html += formatSeconds(LIMIT_DURATION_MIN_MS);
  html += " a ";
  html += formatSeconds(LIMIT_DURATION_MAX_MS);
  html += " s</small>";

  html += "<label>Clics del relé por segundo</label>";
  html += "<input type='number' name='clicks' step='1' min='";
  html += String(LIMIT_CLICKS_MIN);
  html += "' max='";
  html += String(LIMIT_CLICKS_MAX);
  html += "' value='";
  html += String(clicksPerSecond);
  html += "'><small>Permitido: ";
  html += String(LIMIT_CLICKS_MIN);
  html += " a ";
  html += String(LIMIT_CLICKS_MAX);
  html += "</small>";

  html += "<label>Descanso entre toques (segundos)</label>";
  html += "<input type='number' name='cooldown' step='0.5' min='";
  html += formatSeconds(LIMIT_COOLDOWN_MIN_MS);
  html += "' max='";
  html += formatSeconds(LIMIT_COOLDOWN_MAX_MS);
  html += "' value='";
  html += formatSeconds(cooldownMs);
  html += "'><small>Permitido: ";
  html += formatSeconds(LIMIT_COOLDOWN_MIN_MS);
  html += " a ";
  html += formatSeconds(LIMIT_COOLDOWN_MAX_MS);
  html += " s</small>";

  html += "<button type='submit'>Guardar</button></form>";
  html += "<p><small>Los valores se limitan en el ESP32. Este panel no controla la intensidad.</small></p>";
  html += "</div></body></html>";
  return html;
}

void handleRoot() {
  server.send(200, "text/html; charset=utf-8", buildPage(server.hasArg("ok")));
}

void handleSave() {
  long duration = durationMs;
  long clicks = clicksPerSecond;
  long cooldown = cooldownMs;
  if (server.hasArg("duration")) duration = lround(server.arg("duration").toFloat() * 1000.0);
  if (server.hasArg("clicks")) clicks = server.arg("clicks").toInt();
  if (server.hasArg("cooldown")) cooldown = lround(server.arg("cooldown").toFloat() * 1000.0);
  saveSettings(duration, clicks, cooldown);
  server.sendHeader("Location", "/?ok=1");
  server.send(303);
}

// ---------- Arranque y bucle ----------
void setup() {
  Serial.begin(BAUD_RATE);
  pinMode(RELAY_PIN, OUTPUT);
  setRelay(false);  // arranca siempre apagado

  loadSettings();
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASSWORD, 1, 0, 2);  // canal 1, visible, máx. 2 conectados
  server.on("/", HTTP_GET, handleRoot);
  server.on("/save", HTTP_POST, handleSave);
  server.begin();
}

void loop() {
  while (Serial.available() > 0) {
    char command = Serial.read();
    if (command == 'S') {
      startBurst();
    } else if (command == 'X') {
      stopBurst();
    }
  }
  updateBurst();
  server.handleClient();
}