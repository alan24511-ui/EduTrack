// EduTrack: Arduino UNO/Nano + RC522 (MFRC522). Salida serial: "UID: A1B2C3D4".
#include <SPI.h>
#include <MFRC522.h>

constexpr byte PIN_RST = 9;
constexpr byte PIN_SS = 10;
constexpr unsigned long REARM_DELAY_MS = 400;

MFRC522 lector(PIN_SS, PIN_RST);
bool tarjetaEnCampo = false;
unsigned long ultimaDeteccion = 0;

void setup() {
  Serial.begin(9600);
  SPI.begin();
  lector.PCD_Init();
  delay(4);
  Serial.println("EduTrack RFID listo");
}

void loop() {
  if (!lector.PICC_IsNewCardPresent()) {
    if (tarjetaEnCampo && millis() - ultimaDeteccion >= REARM_DELAY_MS) {
      tarjetaEnCampo = false;
    }
    delay(30);
    return;
  }

  if (!lector.PICC_ReadCardSerial()) {
    delay(30);
    return;
  }

  if (!tarjetaEnCampo) {
    Serial.print("UID: ");
    for (byte i = 0; i < lector.uid.size; i++) {
      if (lector.uid.uidByte[i] < 0x10) Serial.print('0');
      Serial.print(lector.uid.uidByte[i], HEX);
    }
    Serial.println();
    tarjetaEnCampo = true;
  }
  ultimaDeteccion = millis();

  lector.PICC_HaltA();
  lector.PCD_StopCrypto1();
  delay(80);
}
