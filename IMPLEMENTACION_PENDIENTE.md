# Implementación pendiente

| Área | Estado / pendiente |
|---|---|
| Autenticación y sesiones | Implementadas; falta validación HTTP contra proyecto Supabase de la instalación. |
| Estudiantes, tutores, tarjetas, horarios, historial y dashboard | Implementados según el esquema compartido; falta validación contra PostgreSQL real y sus políticas RLS/checks. |
| Lector RFID | Arduino + RC522 por USB serial a 9600 baudios; el receptor Python conserva pendientes en SQLite y los envía en ciclos al contrato actual. Pendiente prueba física del hardware y validación contra la API/base reales. |
| Ingesta/reintentos | Encolado local y reintento implementados. El backend solo acepta un evento por solicitud, no ofrece clave de idempotencia ni hora de captura; no puede garantizarse exactamente una vez ante una respuesta perdida. Para esa garantía se necesita ampliar API/base de datos de forma coordinada. |
| Reglas de asistencia | Primera lectura del día = entrada, segunda = salida. Confirmar reglas del plantel para retardos, calendario y ausencias. |
| Seguridad / despliegue | Configurar secretos localmente; revisar CORS, TLS, permisos de la cola SQLite, constraints y RLS antes de producción. |

## Puesta en marcha RFID

Seguir [HARDWARE.md](HARDWARE.md) para cableado RC522-Arduino, carga del firmware, puerto serial, dependencias y operación. Confirmar `EDUTRACK_DEVICE_CODE` activo y coincidencia del token `EDUTRACK_RFID_TOKEN` con `RFID_INGEST_TOKEN`.

## Aspectos que no se han validado

- Lectura real RC522 con el Arduino y la revisión exacta de placa/módulo elegida.
- Envío integrado de lecturas a un backend y una base Supabase reales.
- Desempeño/resistencia de la cola con la carga y retención de registros de producción.
- Restricciones, checks y políticas RLS completas del esquema remoto.
