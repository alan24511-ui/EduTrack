# Arquitectura de EduTrack

## Diseño existente y objetivo

```text
RC522 --SPI--> Arduino Uno --USB serial--> Servicio Python --HTTP--> FastAPI --> PostgreSQL/Supabase
                                                                         ^
                                                                         |
                                                               Angular standalone
```

Angular standalone presenta la aplicación y llama a FastAPI. Bootstrap 5.3.3 está cargado desde CDN. FastAPI reenvía operaciones de autenticación a Supabase Auth usando URL y clave anon del servidor, valida access tokens consultando Supabase Auth, y consulta PostgreSQL con `psycopg`. La clave `service_role` no se necesita para autenticación y nunca se usa desde el frontend.

El backend implementa autenticación OTP, login/logout/perfil, renovación y recuperación de sesión, roles desde `Administradores.Rol`, guardas Angular, códigos de vinculación con hash/expiración/transacción, CRUD de estudiantes, gestión de tarjetas por estudiante, historial, dashboard y recepción RFID autenticada. Los roles administrativos aceptados son `administrador` y `superadministrador`; el tutor se resuelve por `Tutores.auth_user_id`.

## Límites comprobados

- El código de datos se debe probar contra PostgreSQL real y revisar junto con políticas RLS.
- `Credenciales_rfid` tiene vigencias, pero no un campo activo. La API calcula vigencia y permite reemplazar una tarjeta; no hay activación/desactivación independiente.
- `Asistencia` permite una fila por estudiante/fecha: primera lectura = entrada, segunda = salida; lecturas posteriores no cambian la fila diaria. No se calculan retardos, salidas anticipadas o inasistencias sin confirmar reglas escolares.
- El inventario enumera, pero no incluye las expresiones de `ck_admin_rol`, checks de asistencia/vigencia ni políticas RLS.
- El firmware habla por líneas `UID:<hexadecimal>` a 115200 baudios. Python valida, deduplica, reconecta y realiza HTTP autenticado. Falta prueba física.

No se debe crear o aplicar SQL en Supabase hasta obtener y revisar el esquema, sus restricciones y políticas actuales. Ver [IMPLEMENTACION_PENDIENTE.md](IMPLEMENTACION_PENDIENTE.md).
