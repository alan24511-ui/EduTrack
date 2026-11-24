// EduTrack: Arduino UNO + RC522 + HC-05 (Bluetooth serie).
// HC-05 TXD -> D2 (RX SoftwareSerial); HC-05 RXD <- D3 (TX, usar divisor).
#include <SPI.h>
#include <MFRC522.h>
#include <SoftwareSerial.h>

constexpr byte PIN_RST = 9;
constexpr byte PIN_SS = 10;
constexpr byte PIN_BT_RX = 2;
constexpr byte PIN_BT_TX = 3;
constexpr unsigned long REARM_DELAY_MS = 400;

MFRC522 lector(PIN_SS, PIN_RST);
SoftwareSerial bluetooth(PIN_BT_RX, PIN_BT_TX);
bool tarjetaEnCampo = false;
unsigned long ultimaDeteccion = 0;

void setup() {
  bluetooth.begin(9600);
  SPI.begin();
  lector.PCD_Init();
  delay(4);
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
    String mensaje = "UID:";
    for (byte i = 0; i < lector.uid.size; i++) {
      if (lector.uid.uidByte[i] < 0x10) mensaje += '0';
      mensaje += String(lector.uid.uidByte[i], HEX);
    }
    mensaje.toUpperCase();
    bluetooth.println(mensaje);
    tarjetaEnCampo = true;
  }

  ultimaDeteccion = millis();
  lector.PICC_HaltA();
  lector.PCD_StopCrypto1();
  delay(80);
}
