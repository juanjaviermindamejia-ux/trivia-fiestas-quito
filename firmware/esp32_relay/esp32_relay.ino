// Recibe '1' (encender) o '0' (apagar) por serial y controla el relé.
const int RELAY_PIN = 26;
const long BAUD_RATE = 115200;

// Muchos módulos de relé son "activo en bajo": si funciona al revés,
// intercambia HIGH y LOW en estas dos líneas.
const int RELAY_ON = HIGH;
const int RELAY_OFF = LOW;

void setup() {
  Serial.begin(BAUD_RATE);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, RELAY_OFF);
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();
    if (command == '1') {
      digitalWrite(RELAY_PIN, RELAY_ON);
    } else if (command == '0') {
      digitalWrite(RELAY_PIN, RELAY_OFF);
    }
  }
}
