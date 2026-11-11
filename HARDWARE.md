# Hardware y servicio del lector RFID EduTrack

## Arquitectura

```text
RC522 --SPI/GPIO--> Raspberry Pi Zero 2 W --Python/SQLite--> HTTPS/HTTP
                                                           |
                                                           v
                                                FastAPI /rfid/lecturas
                                                           |
                                                           v
                                                PostgreSQL / Supabase
```

La Raspberry controla directamente el RC522. El servicio local separa la captura (`rfid_reader.py`), la cola durable (`queue_store.py`) y la entrega (`synchronizer.py`). El backend conserva su contrato actual `POST /rfid/lecturas`, cuerpo `{"uid":"...", "codigo_dispositivo":"..."}` y encabezado `X-Reader-Token`. No se cambió Angular ni el esquema de datos.

## Conexiones SPI

Conecta con la Raspberry apagada. Usa los números BCM y verifica el pinout del modelo de placa antes de energizar.

| RC522 | Raspberry Pi Zero 2 W | Pin físico | BCM |
|---|---|---:|---:|
| SDA / SS | SPI0 CE0 | 24 | GPIO8 |
| SCK | SPI0 SCLK | 23 | GPIO11 |
| MOSI | SPI0 MOSI | 19 | GPIO10 |
| MISO | SPI0 MISO | 21 | GPIO9 |
| RST | GPIO22 | 15 | GPIO22 |
| GND | GND | 6 | — |
| 3.3V | 3V3 | 1 | — |

El RC522 trabaja a 3.3 V. Aliméntalo desde 3V3; nunca conectes su VCC a 5 V. Las señales GPIO de la Raspberry son de 3.3 V y no toleran 5 V. Mantén los cables SPI cortos y firmes. La Raspberry recibe su alimentación por el conector USB de alimentación según las especificaciones de la placa; evita alimentar el lector y la Pi desde fuentes distintas sin tierra común.

## Instalación en Raspberry Pi OS

1. Instala Raspberry Pi OS actualizado y arranca la Pi. Habilita SPI con `sudo raspi-config` → **Interface Options** → **SPI** → **Enable**, reinicia y confirma que existe `/dev/spidev0.0` (`ls -l /dev/spidev0.0`). Si no aparece, revisa la configuración SPI del sistema y reinicia.
2. Conecta los pines de la tabla con la Pi apagada.
3. Instala Python y soporte GPIO/SPI desde los paquetes del sistema, cuando estén disponibles:

   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip python3-spidev python3-rpi.gpio
   ```

4. Copia o clona EduTrack en la Pi. En `reader_service`, crea el entorno e instala las dependencias:

   ```bash
   cd reader_service
   python3 -m venv --system-site-packages .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   `pi-rc522` provee el controlador `pirc522`; `requests` envía HTTP. SQLite y el resto usado para la cola son parte de Python. El controlador documenta lectura de UID de 4 o 7 bytes; aunque el contrato de FastAPI también admite 10 bytes, esta librería no los obtiene actualmente. Si el paquete de GPIO de la distribución no es compatible con la versión instalada de Python, usa la versión de Raspberry Pi OS/Python soportada por `pi-rc522`; no conectes señales de 5 V como alternativa.

5. Configura variables en el entorno del servicio (no en el repositorio):

   ```bash
   export EDUTRACK_DEVICE_CODE='CODIGO_DE_UN_DISPOSITIVO_ACTIVO'
   export EDUTRACK_RFID_TOKEN='MISMO_VALOR_QUE_RFID_INGEST_TOKEN_EN_FASTAPI'
   export EDUTRACK_RFID_ENDPOINT='https://TU_API/rfid/lecturas'
   export EDUTRACK_RFID_QUEUE='/var/lib/edutrack/readings.sqlite3'
   export EDUTRACK_SYNC_INTERVAL='10'
   export EDUTRACK_BATCH_SIZE='50'
   ```

   `EDUTRACK_DEVICE_CODE` debe existir como dispositivo activo en `Dispositivos`; el token debe coincidir con `RFID_INGEST_TOKEN` del backend. Usa HTTPS al atravesar redes no confiables. Para una ruta bajo `/var/lib`, crea el directorio y otorga permisos de escritura al usuario que ejecuta el lector. No guardes tokens en el control de versiones ni en argumentos de línea de comandos.

6. Inicia el lector:

   ```bash
   source .venv/bin/activate
   python reader_service.py
   ```

   Opciones equivalentes: `--endpoint`, `--device-code`, `--queue`, `--sync-interval` y `--batch-size`. El intervalo predeterminado es 10 segundos y el máximo predeterminado del ciclo es 50 lecturas. `Ctrl+C` detiene limpiamente el proceso; la cola queda en disco.

## Comprobaciones

### Probar la lectura de UID

Con SPI habilitado, RC522 conectado y entorno virtual activado, ejecuta la utilidad diagnóstica sin iniciar la API:

```bash
python read_uid_once.py
```

Acerca una tarjeta: el programa imprime un UID hexadecimal en mayúsculas y termina. Para probar el servicio completo, ejecuta `python reader_service.py`: el log debe indicar `Tarjeta nueva detectada` y una nueva fila encolada. Mantener la tarjeta sobre la antena no debe crear más filas. Retírala y vuelve a acercarla para generar una lectura distinta. La representación hexadecimal conserva ceros iniciales; el driver actual lee UID de 4 o 7 bytes.

La cantidad de pendientes se puede consultar sin exponer UID:

```bash
python -c "import sqlite3; db=sqlite3.connect('$EDUTRACK_RFID_QUEUE'); print(db.execute('select count(*) from pending_readings').fetchone()[0])"
```

### Probar entrega por ciclos

Verifica que la API responde y que `GET /health` está disponible. Configura una tarjeta de prueba en la aplicación y un lector activo. Tras colocar la tarjeta, espera el intervalo de sincronización. En el log se espera `Lote sincronizado`; revisa en la interfaz/historial del sistema el resultado. Swagger (`/docs`) documenta el endpoint actual. Los registros se envían uno por uno al endpoint existente dentro de cada ciclo de hasta `EDUTRACK_BATCH_SIZE`; no hay una ruta de ingesta masiva en el backend actual.

### Verificar almacenamiento sin conexión

1. Detén temporalmente FastAPI o desconecta la red.
2. Lee una tarjeta. El log debe mostrar la cola pendiente y el aviso de fallo de sincronización.
3. Confirma que el contador SQLite aumenta y que el proceso sigue activo.
4. Reinicia el servicio para comprobar persistencia entre reinicios: el contador debe seguir igual.
5. Restaura la conexión. En el siguiente ciclo, los registros aceptados deben quitarse de la cola y el contador disminuir.

SQLite usa WAL y `synchronous=FULL`; conserva la base `readings.sqlite3` junto con sus archivos `-wal`/`-shm` mientras el proceso esté activo. No borres la cola para “resolver” errores de conectividad.

## Reintentos y límites de idempotencia

Se conserva cada fila hasta recibir una respuesta HTTP exitosa; ante fallo de red, timeout o respuesta no exitosa, se detiene el lote y se reintenta en el siguiente intervalo. El backend reconoce lecturas repetidas de la misma tarjeta/dispositivo dentro de una ventana de 4 segundos. Sin embargo, su contrato no acepta un identificador único generado por el lector. Si la API confirma una transacción y la respuesta se pierde, un reintento posterior no se puede distinguir con certeza de una nueva lectura válida. Por esa limitación del contrato actual no es posible garantizar “exactamente una vez” ante fallos ambiguos de red sin añadir idempotencia al backend o al esquema; no se inventó un campo ni una ruta para simular esa garantía.

El timestamp se conserva en la cola local para diagnóstico futuro, pero no se envía: el endpoint actual no admite una hora de captura y asigna la hora de recepción del servidor. Durante una caída de red, las asistencias se registrarán al sincronizarse, no necesariamente a la hora física del escaneo. Si se requiere hora original y procesamiento exactamente una vez, hace falta extender de forma coordinada el contrato/API y la persistencia.

## Seguridad, operación y mantenimiento

- Instala el lector en una caja aislante, protegida de líquidos, polvo conductor y tirones de cables; deja ventilación para la Pi. Usa una fuente estable adecuada para Raspberry Pi Zero 2 W.
- No manipules conexiones con la Pi energizada. No conectes RC522 a 5 V ni a redes eléctricas expuestas.
- Mantén el token fuera de logs y repositorios; restringe permisos del archivo SQLite porque contiene UID y hora local de lecturas.
- Comprueba periódicamente `/health`, el heartbeat del dispositivo, espacio libre, número de pendientes y estado de cables/conectores.
- Si se cambia GPIO, SPI o lector, apaga la Pi antes de modificar el cableado.

El firmware Arduino, el protocolo serial y `pyserial` se retiraron: el lector ya no utiliza un intermediario USB.
