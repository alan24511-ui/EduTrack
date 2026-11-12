# Implementación pendiente

| Área | Estado / pendiente |
|---|---|
| Autenticación y sesiones | Implementadas; falta validación HTTP contra proyecto Supabase de la instalación. |
| Estudiantes, tutores, tarjetas, horarios, historial y dashboard | Implementados según el esquema compartido; falta validación contra PostgreSQL real y sus políticas RLS/checks. |
| Lector RFID | Servicio adaptado a Raspberry Pi Zero 2 W + RC522 por SPI, SQLite persistente y envío en ciclos al contrato actual. Pendiente prueba física en la Pi y revisión de versión/compatibilidad de `pi-rc522` en la imagen objetivo de Raspberry Pi OS. |
| Ingesta/reintentos | Encolado local y reintento implementados. El backend solo acepta un evento por solicitud, no ofrece clave de idempotencia ni hora de captura; no puede garantizarse exactamente una vez ante una respuesta perdida. Para esa garantía se necesita ampliar API/base de datos de forma coordinada. |
| Reglas de asistencia | Primera lectura del día = entrada, segunda = salida. Confirmar reglas del plantel para retardos, calendario y ausencias. |
| Seguridad / despliegue | Configurar secretos localmente; revisar CORS, TLS, permisos de la cola SQLite, constraints y RLS antes de producción. |

## Puesta en marcha RFID

Seguir [HARDWARE.md](HARDWARE.md) para cableado SPI, habilitación de SPI, dependencias y operación. Confirmar `EDUTRACK_DEVICE_CODE` activo y coincidencia del token `EDUTRACK_RFID_TOKEN` con `RFID_INGEST_TOKEN`. La Raspberry no necesita Arduino, puerto serial ni `pyserial`.

## Aspectos que no se han validado

- Lectura real RC522 con los pines GPIO y la revisión exacta de Raspberry Pi OS elegida.
- Envío integrado de lecturas a un backend y una base Supabase reales.
- Desempeño/resistencia de la cola con la carga y retención de registros de producción.
- Restricciones, checks y políticas RLS completas del esquema remoto.
