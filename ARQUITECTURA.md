# Arquitectura de EduTrack

## Diseño existente y objetivo

```text
RC522 --SPI--> Arduino Uno --USB serial--> Servicio Python --HTTP--> FastAPI --> PostgreSQL/Supabase
                                                                         ^
                                                                         |
                                                               Angular standalone
```

Angular standalone presenta la aplicación y llama a FastAPI. Bootstrap 5.3.3 está cargado desde CDN. FastAPI reenvía operaciones de autenticación a Supabase Auth usando URL y clave anon del servidor, valida access tokens consultando Supabase Auth, y consulta PostgreSQL con `psycopg`. La clave `service_role` no se necesita para autenticación y nunca se usa desde el frontend.

El repositorio implementa autenticación de tutor, OTP, login/logout/perfil, renovación y recuperación de sesión, guardas Angular, autorización administrativa básica y códigos de vinculación con hash, expiración y consumo dentro de una transacción. La tabla/columna SQL de `Administradores` usada por el código es `auth_user_id`; la creación del tutor usa `Tutores.auth_user_id` y `Estudiante_Tutor`.

## Límites comprobados

- No se encontraron migraciones, DDL, políticas RLS ni documentación de restricciones de Supabase en el repositorio.
- El backend local no pudo conectarse durante la auditoría: falta el paquete `psycopg` en el Python activo. No se pudo inspeccionar el esquema remoto/local.
- Los componentes de estudiantes, tarjetas, historial y dashboard no tienen lógica de datos conectada.
- El firmware habla por líneas `UID:<hexadecimal>` a 115200 baudios. El proceso Python valida, deduplica, reintenta ante desconexión y hace HTTP; el endpoint de ingestión aún no existe.
- El tipo de evento (entrada/salida), calendario, zona horaria de sesión y deduplicación durable requieren verificar el modelo y las reglas actuales antes de registrar asistencias.
- La tabla/rol de superadministrador no está identificado. Actualmente la separación comprobable distingue administrador (registro en `Administradores`) y tutor.

No se debe crear o aplicar SQL en Supabase hasta obtener y revisar el esquema, sus restricciones y políticas actuales. Ver [IMPLEMENTACION_PENDIENTE.md](IMPLEMENTACION_PENDIENTE.md).
