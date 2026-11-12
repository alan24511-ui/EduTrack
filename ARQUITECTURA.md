# Arquitectura de EduTrack

## Diseño

```text
RC522 --SPI--> Raspberry Pi Zero 2 W --Python--> SQLite local (pendientes)
                                                 |
                                                 | POST individual por ciclo
                                                 v
Angular standalone <--> FastAPI <--> PostgreSQL / Supabase
```

La aplicación web es Angular standalone con Bootstrap. FastAPI gestiona autenticación apoyada en Supabase Auth y consulta PostgreSQL con `psycopg`. En el dispositivo, `rfid_reader.py` lee el RC522 por SPI, `queue_store.py` mantiene una cola SQLite durable y `synchronizer.py` envía las lecturas pendientes al endpoint existente `POST /rfid/lecturas`. El servicio también actualiza `POST /rfid/heartbeat`.

El cuerpo de ingesta sigue siendo `uid` y `codigo_dispositivo`, autenticado por `X-Reader-Token`. No se cambió el frontend ni el esquema de base de datos. El firmware Arduino, el protocolo serial y `pyserial` ya no forman parte del flujo.

## Procesamiento RFID

La Pi conserva los UID como hexadecimal en mayúsculas, con ceros iniciales y longitud de 4, 7 o 10 bytes. El lector solo encola una vez por colocación de tarjeta; se rearma tras detectar que la tarjeta dejó el campo. El proceso sincroniza hasta un lote configurable cada intervalo configurable. Como FastAPI solo expone ingesta individual, un ciclo de lote realiza varios `POST` uno por uno, sin agregar rutas ni cambiar el contrato.

La cola no elimina una lectura hasta recibir HTTP exitoso; los errores dejan registros para el siguiente ciclo. Un UID y código de dispositivo se conservan localmente junto a la hora de captura; esta última no puede viajar al servidor porque el contrato actual no la admite. Ante pérdida de una respuesta después de que el backend haya confirmado la escritura, un reintento no puede garantizar exactamente una vez: el endpoint carece de una clave de idempotencia. El backend sí aplica una ventana de deduplicación de cuatro segundos. Véase [HARDWARE.md](HARDWARE.md).

## Límites pendientes

- Las consultas SQL y las reglas RLS/checks deben contrastarse con el esquema real de Supabase antes de producción.
- Las reglas actuales de asistencia son primera lectura diaria = entrada, segunda = salida; posteriores no cambian la fila diaria.
- La integración nueva SPI/RC522 debe validarse en la Raspberry Pi física; la ejecución en otro equipo no prueba el cableado ni el lector.
- El timestamp local no se utiliza para retrofechar asistencia; el servidor registra la hora de llegada.
