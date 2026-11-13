# Lector RFID Arduino + RC522

## Arquitectura

```text
RC522 --SPI--> Arduino --USB serial 9600 baudios--> Python + cola SQLite
                                                  | POST /rfid/lecturas
                                                  v
                                      FastAPI --> PostgreSQL / Supabase
```

El Arduino solo lee el RC522 y emite una línea por tarjeta, por ejemplo `UID: A1B2C3D4`. Python escucha el puerto serial, guarda las lecturas en `reader_service/data/readings.sqlite3` y sincroniza hasta el tamaño de lote configurado con el endpoint existente `POST /rfid/lecturas`. El endpoint acepta un evento por solicitud, por lo que cada ciclo del lote hace varias solicitudes. La cola elimina cada registro únicamente tras recibir una respuesta HTTP exitosa. También se usa `POST /rfid/heartbeat` mientras el receptor está ejecutándose.

## Conectar RC522 a Arduino UNO/Nano

Haz las conexiones con el Arduino desconectado del USB. El RC522 usa señales de 3.3 V: conecta VCC a 3.3 V, nunca a 5 V. Los nombres de pines SPI dependen de la placa; en UNO/Nano son:

| RC522 | Arduino UNO/Nano |
|---|---|
| SDA / SS | D10 |
| SCK | D13 |
| MOSI | D11 |
| MISO | D12 |
| RST | D9 |
| GND | GND |
| 3.3V | 3.3V |

En Arduino Mega, usa SS D53, SCK D52, MOSI D51, MISO D50; cambia `PIN_SS` a 53 en el firmware. Comprueba el pinout de la placa concreta y no conectes señales de 5 V al módulo.

## Cargar el firmware

1. Instala Arduino IDE y la biblioteca **MFRC522** (Miguel Balboa) desde Library Manager.
2. Abre `reader_service/arduino/lector_rfid.ino`.
3. Selecciona la placa y el puerto correctos y carga el sketch.
4. Abre Serial Monitor a **9600 baudios**. Al acercar una tarjeta debe aparecer `UID: ...`. Una tarjeta que permanece sobre el lector no debe generar líneas repetidas; retírala y preséntala de nuevo para leerla otra vez.
5. Cierra Serial Monitor antes de iniciar Python, ya que solo un programa puede usar el puerto a la vez.

## Configurar e iniciar Python

Se requiere Python 3.10 o posterior. Desde la raíz del repositorio:

```bash
cd reader_service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configura las credenciales y el puerto del Arduino en el shell. En Linux suele ser `/dev/ttyACM0` o `/dev/ttyUSB0`; en Windows, `COM3` (consulta el Administrador de dispositivos); en macOS, `/dev/cu.usbmodem...`.

```bash
export EDUTRACK_SERIAL_PORT=/dev/ttyACM0
export EDUTRACK_SERIAL_BAUD=9600
export EDUTRACK_DEVICE_CODE='CODIGO_DE_UN_DISPOSITIVO_ACTIVO'
export EDUTRACK_RFID_TOKEN='MISMO_VALOR_QUE_RFID_INGEST_TOKEN_EN_FASTAPI'
export EDUTRACK_RFID_ENDPOINT='http://localhost:8000/rfid/lecturas'
export EDUTRACK_RFID_QUEUE='./data/readings.sqlite3'
export EDUTRACK_SYNC_INTERVAL=10
export EDUTRACK_BATCH_SIZE=50
export EDUTRACK_DEDUPE_SECONDS=2
python reader_service.py
```

El usuario del sistema debe tener permiso para abrir el puerto serial (en Linux puede requerir pertenecer al grupo `dialout` y volver a iniciar sesión). El programa reintenta la conexión USB si se desconecta. `EDUTRACK_RFID_TOKEN` debe coincidir con `RFID_INGEST_TOKEN` del backend y el código debe corresponder a un lector activo de `Dispositivos`. No guardes esos valores en Git. Los mismos ajustes se pueden pasar con `--serial-port`, `--baud-rate`, `--device-code`, `--endpoint`, `--queue`, `--sync-interval`, `--batch-size` y `--dedupe-seconds`.

El intervalo predeterminado de envío es 10 segundos y el lote predeterminado es de 50. La cola SQLite es durable entre reinicios. Si ocurre un fallo HTTP o de red, las lecturas no confirmadas permanecen pendientes para el siguiente ciclo. El filtro local evita la repetición del mismo UID durante dos segundos; Arduino además informa una sola vez por presencia de tarjeta.

## Prueba de extremo a extremo

1. Configura las variables de conexión de Supabase y `RFID_INGEST_TOKEN` en `backend/.env`, y arranca FastAPI desde `backend` con `uvicorn app.main:app --reload`.
2. Comprueba `http://localhost:8000/health` y `http://localhost:8000/health/db`.
3. Registra una tarjeta de prueba en EduTrack y confirma que el código del dispositivo lector está activo.
4. Carga el firmware, conecta Arduino por USB, cierra Serial Monitor y ejecuta `python reader_service.py` con las variables anteriores.
5. Presenta la tarjeta. El log debe indicar que se encoló y, al sincronizar, que el lote fue enviado. Comprueba el evento en la API/Swagger (`/docs`) y la asistencia en la aplicación.
6. Para validar la cola offline, detén temporalmente el backend, presenta una tarjeta y confirma que el proceso mantiene lecturas pendientes. Inicia de nuevo el backend: el siguiente ciclo las enviará y retirará de SQLite.

## Contrato, hora y reintentos

El receptor reutiliza `POST /rfid/lecturas` con cuerpo `{"uid":"...", "codigo_dispositivo":"..."}` y encabezado `X-Reader-Token`; no se añadió un endpoint por lotes ni se cambió el esquema. FastAPI valida UID de 4, 7 o 10 bytes, verifica que el dispositivo esté activo y conserva la lógica de tarjetas registradas/vigentes. Asigna el momento del evento con la zona `America/Mexico_City`. La hora de captura se guarda localmente para diagnóstico, pero el contrato actual no la envía: lecturas pendientes se registran en el servidor al sincronizar.

Como el endpoint no acepta clave de idempotencia, si FastAPI confirma una escritura pero se pierde su respuesta, un reintento puede volver a llegar; el backend aplica su deduplicación actual de cuatro segundos. No es posible garantizar exactamente una vez durante ese fallo ambiguo sin extender el contrato y persistencia.
