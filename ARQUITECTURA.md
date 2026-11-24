# Arquitectura de EduTrack

```text
RC522 --SPI--> Arduino UNO --HC-05/RFCOMM 9600--> receptor Bluetooth --> FastAPI --> PostgreSQL/Supabase
Angular ----------------------------------------------------------HTTP----^
```

El proceso `reader_service/bluetooth_receiver.py` mantiene RFCOMM abierto, informa heartbeats y envía los UID al backend. FastAPI no abre puertos de hardware. Las lecturas fuera de una sesión administrativa continúan por `POST /rfid/lecturas`, conservando las reglas existentes de dispositivo, tarjeta, vigencia, antirrebote, entrada/salida y persistencia.

Al asociar una tarjeta desde Alumnos, FastAPI abre una sesión temporal. El receptor ofrece cada UID a `POST /rfid/reader/capture`; si hay sesión activa, ese UID se consume para la asociación y no se procesa como asistencia. Si no hay sesión, continúa por el endpoint normal de lecturas. Estado, asociación y cancelación requieren sesión administrativa; el receptor autentica la captura con `RFID_INGEST_TOKEN`.
