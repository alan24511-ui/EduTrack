# Arquitectura de EduTrack

## Diseño

```text
Arduino + RC522 --USB Serial--> Python + SQLite (cola local)
                                      |
                                      | POST /rfid/lecturas
                                      v
Angular <--> FastAPI <--> PostgreSQL / Supabase
```

Arduino se limita a leer tarjetas RC522 y enviar el UID en texto serial (`UID: A1B2C3D4`, 9600 baudios). El servicio local de Python interpreta ese protocolo, elimina repeticiones breves, guarda lecturas en SQLite y las sincroniza por ciclos. FastAPI valida el UID, verifica el dispositivo y la tarjeta, registra asistencia y se conecta a PostgreSQL/Supabase. Angular consume la API sin cambios a su navegación, vistas o roles.

## Componentes

- `reader_service/arduino/lector_rfid.ino`: firmware para RC522 mediante la biblioteca MFRC522.
- `reader_service/reader_service.py` y `serial_reader.py`: recepción USB serial y coordinación del envío.
- `reader_service/queue_store.py`: cola local durable SQLite.
- `reader_service/synchronizer.py`: envío del lote al endpoint actual, una lectura por solicitud.
- `backend/app/routes/rfid.py`: endpoints autenticados de lectura y heartbeat.

El endpoint acepta `uid` y `codigo_dispositivo`, usa `X-Reader-Token` y valida tarjetas registradas, vigencia y estado del lector. La hora del registro la asigna FastAPI con `America/Mexico_City`. No se modificó el esquema de base de datos. Arduino no realiza llamadas HTTP ni se conecta a Supabase.

## Reintentos y límites

Python conserva cada fila hasta una respuesta HTTP exitosa. Si falla el envío, pausa el lote y reintenta en el siguiente ciclo. El backend deduplica lecturas repetidas de una tarjeta/dispositivo durante cuatro segundos y el receptor filtra duplicados inmediatos durante dos segundos por defecto. El contrato de la API no admite un identificador idempotente; una respuesta perdida después de un commit puede dar lugar a un reintento ambiguo. Tampoco se envía hora de captura local, así que una lectura encolada offline se registra con la hora de recepción del backend.

La integración de hardware requiere prueba física con Arduino, RC522 y puerto USB de la computadora. Consulta [HARDWARE.md](HARDWARE.md) para cableado, instalación, configuración y verificación extremo a extremo.
