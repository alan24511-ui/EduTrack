# Implementación pendiente

Última auditoría: 2026-11-08. Rama `chato`; árbol inicial limpio. No se aplicaron cambios a Supabase ni se hicieron commits.

| Etapa / módulo | Estado | Trabajo realizado / pendiente |
|---|---|---|
| 1. Autenticación y sesiones | PARCIAL | Auth existente conservado; se añadieron endpoints FastAPI de refresh, reenvío OTP, solicitud/restablecimiento de contraseña, UI para reenvío y recuperación, servicio Angular de sesión y reintento al recibir 401. Falta validar HTTP con Supabase configurado. |
| 2. Gestión de estudiantes | BLOQUEADO | La pantalla existe sin integración. Falta esquema real (columnas, llaves, restricciones y políticas) para diseñar consultas seguras y formularios fieles. |
| 3. Tarjetas RFID | BLOQUEADO | La pantalla existe sin integración. Falta esquema real de `Credenciales_rfid`, vigencia, relación y reglas de activación. |
| 4. Vinculación de tutores | PARCIAL | Flujo backend y frontend existente; usa hash, expiración y transacción. Falta verificar compatibilidad con esquema real, carreras/constraints y ejecutar integración con base configurada. |
| 5. Arduino + RC522 | PARCIAL | Firmware SPI y protocolo de línea creados; no probado con dispositivo físico. |
| 6. Servicio Python | PARCIAL | Cliente serial configurable, validación, deduplicación, reintento y pruebas simuladas creados. Falta endpoint receptor seguro FastAPI y prueba con Arduino físico. |
| 7. Asistencias | BLOQUEADO | No hay modelo, reglas de entrada/salida, calendario ni tabla identificable en repo. No se inventó regla ni se registran datos. |
| 8. Historial | BLOQUEADO | Pantalla existe sin datos; depende del esquema de asistencia y permisos tutor-estudiante. |
| 9. Dashboard | BLOQUEADO | Vista estática; no hay consultas reales. Estado del lector tampoco tiene mecanismo de heartbeat. |
| 10. Seguridad y pruebas finales | PARCIAL | Guards Angular y dependencias admin FastAPI existentes; se dejó de usar `service_role` como fallback para llamadas Auth. Sin schema/RLS ni configuración no se puede auditar autorización real. Pruebas se reportan abajo. |
| Documentación | PARCIAL | README, arquitectura, hardware y este registro actualizados; faltan valores de configuración reales, esquema y reglas del plantel. |

## Requisitos manuales para desbloquear

1. Proporcionar DDL o exportación de solo esquema de las tablas implicadas (`Estudiantes`, `Credenciales_rfid`, `Tutores`, `Administradores`, `Estudiante_Tutor` y asistencia), constraints e índices; incluir definición de `Codigos_vinculacion`.
2. Revisar políticas RLS existentes y entregar criterios de rol superadministrador. No compartir claves privadas en el repositorio ni chat.
3. Configurar en `backend/.env` los datos de conexión PostgreSQL y `SUPABASE_URL`, `SUPABASE_ANON_KEY`; configurar plantillas/canal OTP de Supabase. `SUPABASE_SERVICE_ROLE_KEY` no es requerido por las funciones actuales.
4. Definir formalmente cuándo una lectura es entrada o salida, tolerancia de duplicados, calendario escolar y cómo calcular inasistencias. La zona horaria objetivo es `America/Mexico_City`.
5. Para verificación física, disponer de Arduino Uno, módulo RC522, adaptador de nivel lógico 5V→3.3V y tarjeta compatible.

## Evidencia de pruebas de esta revisión

- `python -m unittest` en `reader_service`: 2 pruebas pasaron; son líneas serial simuladas.
- `npm run build`: compilación Angular exitosa con dos warnings NG8113 preexistentes (imports sin uso en `Admin` y `App`).
- `npm test -- --watch=false`: 11 archivos y 16 pruebas Angular pasaron.
- `python -m py_compile app/*.py app/routes/*.py tests/*.py`: sintaxis backend válida; esto no sustituye las pruebas unitarias ni HTTP.
- `git diff --check`: sin errores de whitespace.
- Suite backend original: no ejecutable en el Python activo por `ModuleNotFoundError: fastapi`; el intento de inspección de PostgreSQL falló por `ModuleNotFoundError: psycopg`. No se instalaron dependencias ni se conectó a una base.
- No se probaron llamadas HTTP de Auth: no hay proyecto Supabase verificable disponible en esta auditoría.
- No se probó hardware físico. La simulación de líneas seriales no se presenta como prueba del lector.
