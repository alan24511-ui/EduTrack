// EduTrack RFID capture protocol v1 over USB Serial at 9600 baud.
// RC522: SDA/SS=10, RST=9, MOSI=11, MISO=12, SCK=13, 3.3V and GND.
#include <SPI.h>
#include <MFRC522.h>

constexpr byte PIN_RST = 9;
constexpr byte PIN_SS = 10;
constexpr unsigned long REARM_DELAY_MS = 600;
constexpr byte VERSION_REG = 0x37;

MFRC522 lector(PIN_SS, PIN_RST);
bool lectorOk = false;
bool capturaActiva = false;
bool tarjetaEnCampo = false;
unsigned long ultimaDeteccion = 0;
char comando[20];
byte comandoPos = 0;

void iniciarRC522() {
  lector.PCD_Init();
  delay(50);
  const byte version = lector.PCD_ReadRegister(VERSION_REG);
  lectorOk = version != 0x00 && version != 0xFF;
}

void reportarEstado() {
  Serial.print("READY:EDUTRACK_RFID:1:");
  Serial.println(lectorOk ? "OK" : "ERR:RC522");
  if (!lectorOk) Serial.println("ERROR:RC522_INIT");
}

void procesarComando(const char* texto) {
  if (strcmp(texto, "PING") == 0) {
    if (!lectorOk) iniciarRC522();
    reportarEstado();
  } else if (strcmp(texto, "READ") == 0) {
    if (!lectorOk) {
      Serial.println("ERROR:RC522_INIT");
    } else {
      capturaActiva = true;
      Serial.println("CAPTURING");
    }
  } else if (strcmp(texto, "CANCEL") == 0) {
    capturaActiva = false;
    tarjetaEnCampo = false;
    Serial.println("CANCELLED");
  }
}

void leerComandos() {
  while (Serial.available() > 0) {
    const char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      comando[comandoPos] = '\0';
      procesarComando(comando);
      comandoPos = 0;
    } else if (comandoPos < sizeof(comando) - 1) {
      comando[comandoPos++] = c;
    } else {
      comandoPos = 0;
    }
  }
}

void setup() {
  Serial.begin(9600);
  SPI.begin();
  iniciarRC522();
  reportarEstado();
}

void loop() {
  leerComandos();
  if (!capturaActiva || !lectorOk) return;

  if (!lector.PICC_IsNewCardPresent()) {
    if (tarjetaEnCampo && millis() - ultimaDeteccion >= REARM_DELAY_MS) tarjetaEnCampo = false;
    delay(20);
    return;
  }
  if (!lector.PICC_ReadCardSerial()) return;

  if (!tarjetaEnCampo) {
    Serial.print("UID: ");
    for (byte i = 0; i < lector.uid.size; i++) {
      if (lector.uid.uidByte[i] < 0x10) Serial.print('0');
      Serial.print(lector.uid.uidByte[i], HEX);
    }
    Serial.println();
    tarjetaEnCampo = true;
    capturaActiva = false;
  }
  ultimaDeteccion = millis();
  lector.PICC_HaltA();
  lector.PCD_StopCrypto1();
  delay(40);
}
