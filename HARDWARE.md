# Lector RFID con Arduino UNO y RC522

## Arquitectura

```text
RC522 --SPI--> Arduino UNO --USB Serial 9600--> FastAPI persistente --> PostgreSQL/Supabase
                                                        ^
Angular -------------------------------- HTTP -----------|
```

FastAPI corre en la computadora conectada al Arduino. Mantiene abierto el puerto USB, detecta el dispositivo y vuelve a conectarse tras una desconexión. Cada UID se procesa con la misma lógica del endpoint `/rfid/lecturas`. La captura administrativa de tarjetas en Alumnos también usa ese lector.

## Cableado

| RC522 | Arduino UNO |
|---|---|
| SDA / SS | D10 |
| SCK | D13 |
| MOSI | D11 |
| MISO | D12 |
| RST | D9 |
| VCC | 3.3V |
| GND | GND |

El RC522 trabaja a 3.3 V. No conectes VCC ni sus señales a 5 V.

## Cargar el firmware

1. Instala Arduino IDE y, desde Library Manager, la biblioteca **MFRC522** de Miguel Balboa.
2. Abre `reader_service/arduino/lector_rfid.ino`, selecciona **Arduino Uno** y el puerto USB correcto.
3. Pulsa **Subir**. Cierra Arduino IDE o Serial Monitor después de la carga para liberar el puerto.

El firmware no usa HC-05, Bluetooth, comandos AT ni `SoftwareSerial`. Mantiene las conexiones SPI de la tabla.

## Preparar Fedora y FastAPI

Identifica el puerto Arduino:

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

Uno de los patrones puede no encontrar archivos. Configura `backend/.env` con credenciales de PostgreSQL y Supabase, y estas variables RFID:

```dotenv
ARDUINO_PORT=/dev/ttyACM0
ARDUINO_BAUDRATE=9600
ARDUINO_DEVICE_CODE=CODIGO_DE_UN_DISPOSITIVO_EXISTENTE
RFID_INGEST_TOKEN=un_token_aleatorio_compartido
```

`ARDUINO_PORT` puede quedar vacío para detección automática. `ARDUINO_DEVICE_CODE` tiene que ser el código de un registro ya existente y activo en la tabla `"Dispositivos"`; no se crea ni modifica el esquema. El backend usa el token de ingesta existente al pasar cada lectura por la lógica de `/rfid/lecturas`.

Instala dependencias e inicia el backend:

```bash
cd /home/chato/EduTrack/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`pyserial` ya figura en `backend/requirements.txt`. Angular sigue usando HTTP hacia FastAPI y no requiere cambios de diseño.

## Permisos del puerto

Comprueba los permisos y grupos:

```bash
ls -l /dev/ttyACM0
groups
```

Si el grupo del dispositivo es `dialout`, agrega tu usuario y vuelve a iniciar sesión:

```bash
sudo usermod -aG dialout "$USER"
```

Usa el grupo que muestre `ls -l` si fuera diferente. Cierra Serial Monitor y otros programas que puedan ocupar el puerto. FastAPI y el receptor legado de EduTrack respetan un bloqueo compartido para impedir que ambos abran el puerto a la vez.

## Protocolo y verificación

El puerto usa 9600 baudios. Arduino envía una línea por mensaje:

```text
EDUTRACK_RFID:INICIADO
EDUTRACK_RFID:UID:04A1B2C3
EDUTRACK_RFID:ERROR:RC522_INIT
```

Cada byte del UID se representa con dos dígitos hexadecimales. El firmware emite una sola lectura mientras la tarjeta está presente; retírala y vuelve a acercarla para leerla otra vez.

Para inspeccionar el flujo sin FastAPI, detén el backend y abre temporalmente el puerto con Serial Monitor a 9600 baudios o `screen /dev/ttyACM0 9600`. Cierra ese programa antes de reiniciar FastAPI. Revisa `http://localhost:8000/health`, `/health/db` y, autenticado como administrador, `GET /rfid/reader/status`.

Después de iniciar FastAPI, presenta una tarjeta registrada: la respuesta y los logs deben mostrar su resultado, y las tablas existentes `"Asistencia"` y `"Registros_accesos"` reciben los eventos según la regla actual. UID desconocido, vigencia vencida y dispositivo inactivo se rechazan o registran según la lógica existente. El backend aplica deduplicación de cuatro segundos.

Para verificar la reconexión, desconecta y vuelve a conectar el Arduino. FastAPI explora el puerto de nuevo y los logs deben mostrar la reconexión en unos segundos.

Las pruebas simuladas de backend cubren el formato, el filtrado de diagnósticos, la reconexión, las lecturas conocidas/desconocidas/vencidas y duplicados. Requieren hardware real la inicialización efectiva del RC522, la lectura por SPI, la recepción física por USB y la recuperación tras reconectar el cable.
