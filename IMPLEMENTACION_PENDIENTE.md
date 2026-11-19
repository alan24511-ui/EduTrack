# Implementación pendiente

| Área | Estado / pendiente |
|---|---|
| Autenticación y sesiones | Implementadas; falta validación HTTP contra proyecto Supabase de la instalación. |
| Estudiantes, tutores, tarjetas, horarios, historial y dashboard | Implementados según el esquema compartido; falta validación contra PostgreSQL real y sus políticas RLS/checks. |
| Lector RFID | Arduino + RC522 por USB serial a 9600 baudios; FastAPI procesa UID directamente y se reconecta automáticamente. Requiere validación física y contra la API/base reales. |
| Reglas de asistencia | Se conserva la regla implementada: primera lectura diaria = entrada, segunda = salida. Confirmar reglas del plantel para retardos, calendario y ausencias. |
| Seguridad / despliegue | Configurar secretos localmente; revisar CORS, TLS, constraints y RLS antes de producción. |

## Puesta en marcha RFID

Seguir [HARDWARE.md](HARDWARE.md) para cableado RC522-Arduino, carga del firmware, puerto serial, dependencias y operación. Configurar `ARDUINO_DEVICE_CODE` con un registro existente y activo, `ARDUINO_PORT` (o dejarlo vacío para autodetección), `ARDUINO_BAUDRATE=9600` y `RFID_INGEST_TOKEN`.

## Aspectos que no se han validado

- Inicialización RC522 y lectura real Arduino por SPI.
- Reconexión USB con el equipo y cable concretos.
- Envío integrado contra la API y base Supabase reales.
- Constraints y políticas RLS completas del esquema remoto.
