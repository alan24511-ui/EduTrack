#include <SPI.h>
#include <MFRC522.h>

// Arduino Uno wiring: SS/SDA=10, RST=9; SPI uses pins 11,12,13.
#define SS_PIN 10
#define RST_PIN 9

MFRC522 reader(SS_PIN, RST_PIN);
String ultimoUid = "";
unsigned long ultimaLectura = 0;
const unsigned long INTERVALO_REENVIO_MS = 1800;

String uidHex(const MFRC522::Uid &uid) {
  String valor;
  valor.reserve(uid.size * 2);
  for (byte i = 0; i < uid.size; i++) {
    if (uid.uidByte[i] < 0x10) valor += '0';
    valor += String(uid.uidByte[i], HEX);
  }
  valor.toUpperCase();
  return valor;
}

void setup() {
  Serial.begin(115200);
  SPI.begin();
  reader.PCD_Init();
}

void loop() {
  if (!reader.PICC_IsNewCardPresent() || !reader.PICC_ReadCardSerial()) return;

  const String uid = uidHex(reader.uid);
  const unsigned long ahora = millis();
  if (uid != ultimoUid || ahora - ultimaLectura >= INTERVALO_REENVIO_MS) {
    Serial.print("UID:");
    Serial.println(uid);
    ultimoUid = uid;
    ultimaLectura = ahora;
  }

  reader.PICC_HaltA();
  reader.PCD_StopCrypto1();
  delay(100);
}
