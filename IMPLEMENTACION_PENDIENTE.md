# Implementación pendiente

| Área | Estado / pendiente |
|---|---|
| Autenticación y sesiones | Implementadas; falta validación HTTP contra proyecto Supabase de la instalación. |
| Estudiantes, tutores, tarjetas, horarios, historial y dashboard | Implementados según el esquema compartido; falta validación contra PostgreSQL real y sus políticas RLS/checks. |
| Lector RFID | Arduino + RC522 + HC-05 por Bluetooth RFCOMM a 9600 baudios; el receptor Python reintenta la conexión y entrega UID a FastAPI. Requiere validación física y contra la API/base reales. |
| Reglas de asistencia | Se conserva la regla implementada: primera lectura diaria = entrada, segunda = salida. Confirmar reglas del plantel para retardos, calendario y ausencias. |
| Seguridad / despliegue | Configurar secretos localmente; revisar CORS, TLS, constraints y RLS antes de producción. |

## Puesta en marcha RFID

Seguir [HARDWARE.md](HARDWARE.md) para cableado RC522-Arduino-HC-05, carga del firmware, enlace RFCOMM, dependencias y operación. Configurar `EDUTRACK_DEVICE_CODE` en el receptor con un registro existente y activo y `RFID_INGEST_TOKEN` en backend y receptor.

## Aspectos que no se han validado

- Inicialización RC522 y lectura real Arduino por SPI.
- Reconexión Bluetooth RFCOMM con el módulo concreto.
- Envío integrado contra la API y base Supabase reales.
- Constraints y políticas RLS completas del esquema remoto.
