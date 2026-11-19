# Arquitectura de EduTrack

```text
RC522 --SPI--> Arduino UNO --USB Serial 9600--> FastAPI --> PostgreSQL/Supabase
                                            ^
Angular standalone ------------------ HTTP --|
```

FastAPI administra una instancia persistente de `backend/app/rfid_reader.py` desde el ciclo de vida de la aplicación. Un hilo detecta puertos USB, valida el mensaje de inicialización del protocolo `EDUTRACK_RFID`, procesa UID válidos sin bloquear las rutas HTTP y vuelve a explorar tras desconexiones. El bloqueo de puerto compartido impide que el receptor legado lo abra simultáneamente.

El firmware `reader_service/arduino/lector_rfid.ino` lee el RC522 por SPI y envía mensajes ASCII a 9600 baudios. Cada UID aparece como `EDUTRACK_RFID:UID:<HEX>`; inicio y errores usan el mismo prefijo para que el backend descarte diagnósticos. El sketch no usa Bluetooth ni SoftwareSerial.

Cada UID en operación normal sigue la lógica existente de `POST /rfid/lecturas`: verifica el dispositivo en `"Dispositivos"`, la tarjeta y sus fechas en `"Credenciales_rfid"`, luego aplica la regla de entrada/salida y registra en las tablas existentes. La hora se crea en `America/Mexico_City`. El endpoint administrativo de asociación sigue disponible y captura una tarjeta con el mismo puerto serial.

`GET /rfid/reader/status`, asociación y cancelación requieren sesión administrativa. La lectura automática usa `ARDUINO_DEVICE_CODE` (registro activo existente) y `RFID_INGEST_TOKEN`. Angular continúa comunicándose con FastAPI por HTTP. Consulta `HARDWARE.md` para el cableado, instalación y pruebas.
