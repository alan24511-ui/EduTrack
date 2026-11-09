# Implementación pendiente

Última auditoría: 2026-11-08. Rama `chato`; árbol inicial limpio. No se aplicaron cambios a Supabase ni se hicieron commits.

| Etapa / módulo | Estado | Trabajo realizado / pendiente |
|---|---|---|
| 1. Autenticación y sesiones | PARCIAL | Auth existente conservado; refresh, OTP resend/recovery, restablecimiento, UI y renovación ante 401. Roles `administrador`/`superadministrador` se leen de `Administradores.Rol`; falta validación HTTP real. |
| 2. Gestión de estudiantes | PARCIAL | CRUD, filtros y tutores vinculados conectados según esquema recibido; falta prueba contra PostgreSQL real y revisión RLS. |
| 3. Tarjetas RFID | PARCIAL | Registro, búsqueda UID, vigencia y reemplazo implementados. No hay columna activa, por lo que falta activación/desactivación independiente y captura de UID desde la UI. |
| 4. Vinculación de tutores | PARCIAL | Flujo backend y frontend existente; usa hash, expiración y transacción. Falta verificar compatibilidad con esquema real, carreras/constraints y ejecutar integración con base configurada. |
| 5. Arduino + RC522 | PARCIAL | Firmware SPI y protocolo de línea creados; no probado con dispositivo físico. |
| 6. Servicio Python | PARCIAL | Cliente serial, token compartido, validación, deduplicación y reconexión. Endpoint FastAPI creado; falta prueba HTTP y hardware. |
| 7. Asistencias | PARCIAL | Primera lectura diaria = entrada, segunda = salida y las posteriores no alteran la fila única diaria. Falta validar reglas escolares y probar base real. |
| 8. Historial | PARCIAL | Filtros de fecha/estudiante/grupo y autorización de tutor implementados; falta integración/RLS real. |
| 9. Dashboard | PARCIAL | Métricas/tablas/dispositivos usan datos reales; inasistencias quedan `null` sin calendario escolar. Falta prueba integrada. |
| 10. Seguridad y pruebas finales | PARCIAL | Guards Angular y dependencias admin FastAPI existentes; se dejó de usar `service_role` como fallback para llamadas Auth. Sin schema/RLS ni configuración no se puede auditar autorización real. Pruebas se reportan abajo. |
| Documentación | PARCIAL | README, arquitectura, hardware y este registro actualizados; faltan secretos/configuración local, checks completos y reglas del plantel. |

## Requisitos manuales para desbloquear

1. Configurar PostgreSQL, Supabase Auth/OTP, `SUPABASE_URL`, `SUPABASE_ANON_KEY` y un `RFID_INGEST_TOKEN` aleatorio en `backend/.env`.
2. Confirmar un dispositivo activo en `Dispositivos`; configurar `EDUTRACK_DEVICE_CODE` y `EDUTRACK_RFID_TOKEN` en el servicio local con el mismo token.
3. Revisar expresiones reales de `ck_admin_rol`, checks de asistencia/vigencia y políticas RLS; el inventario recibido solo listó sus nombres.
4. Confirmar reglas de entrada/salida, retardo, calendario y ausencias. La regla actual usa primera lectura para entrada y segunda para salida.
5. Para verificación física, disponer de Arduino Uno, RC522, adaptación de nivel lógico 5V→3.3V y tarjeta compatible.

## Evidencia de pruebas de esta revisión

- `npm run build`: compilación Angular exitosa con dos warnings NG8113 de imports sin uso en `Admin` y `App`.
- `npm test -- --watch=false`: 11 archivos y 16 pruebas Angular pasaron.
- `python -m py_compile app/*.py app/routes/*.py tests/*.py`: sintaxis backend válida. `PYTHONPATH=. python tests/test_attendance_rules.py`: 3 pruebas pasaron.
- `python -m unittest` en `reader_service`: 2 pruebas de protocolo serial simulado pasaron.
- `git diff --check`: sin errores de whitespace.
- Suite backend HTTP/roles: no ejecutable en el Python activo por `ModuleNotFoundError: fastapi`; el intento de inspección de PostgreSQL falló por `ModuleNotFoundError: psycopg`. No se instalaron dependencias ni se conectó a una base.
- No se probaron llamadas HTTP de Auth: no hay proyecto Supabase verificable disponible en esta auditoría.
- No se probó hardware físico. La simulación de líneas seriales no se presenta como prueba del lector.
