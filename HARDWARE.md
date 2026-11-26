# Lector RFID EduTrack por Bluetooth HC-05

## Flujo

```text
RC522 --SPI--> Arduino UNO/Nano --HC-05/RFCOMM--> bluetooth_receiver.py --> FastAPI --> PostgreSQL
Angular ----------------------------------------------------------------HTTP----^
```

El HC-05 es el único transporte RFID en ejecución. FastAPI no abre conexiones físicas al lector. El receptor mantiene `/dev/rfcomm0` abierto y envía las lecturas normales a `POST /rfid/lecturas`. Durante una asociación iniciada desde Alumnos, entrega el siguiente UID a la sesión administrativa y no lo registra como asistencia.

## Cableado

| RC522 | Arduino UNO |
|---|---|
| SDA / SS | D10 |
| SCK | D13 |
| MOSI | D11 |
| MISO | D12 |
| RST | D9 |
| VCC | 3.3 V |
| GND | GND |

El RC522 requiere 3.3 V; no conectes sus señales a 5 V.

| HC-05 | Arduino UNO |
|---|---|
| TXD | D2 (RX de SoftwareSerial) |
| RXD | D3 (TX de SoftwareSerial), con divisor de voltaje |
| GND | GND común |
| VCC | Según la placa del módulo |

## Firmware y configuración

Carga `reader_service/arduino/lector_rfid/lector_rfid.ino` al Arduino. El sketch manda por Bluetooth una línea `UID:<HEX>` al leer una tarjeta. El cable de programación solo se usa para cargar el firmware; el backend no lo utiliza para leer tarjetas.

En `backend/.env` configura las credenciales habituales y:

```dotenv
INGESTA_TOKEN=secreto_generado_localmente
RFID_INGEST_TOKEN=token_legacy_para_heartbeat_y_captura
RFID_DEBOUNCE_SECONDS=5
```

Genera `INGESTA_TOKEN` con `python -c "import secrets; print(secrets.token_urlsafe(48))"`. En el receptor exporta el mismo valor como `EDUTRACK_INGESTA_TOKEN`. El código debe identificar un dispositivo existente y activo en la tabla `"Dispositivos"`. `RFID_INGEST_TOKEN`/`EDUTRACK_RFID_TOKEN` mantienen el flujo previo de heartbeat y captura administrativa.

## Conectar el HC-05 en Fedora

Instala BlueZ y crea el dispositivo RFCOMM. Sustituye la dirección por la del módulo enlazado:

```bash
sudo dnf install bluez bluez-tools
sudo systemctl enable --now bluetooth
sudo rfcomm release 0 2>/dev/null || true
sudo rfcomm connect 0 98:D3:32:11:6F:25 1
```

Deja `rfcomm connect` corriendo. En otra terminal, inicia el receptor:

```bash
cd /home/chato/EduTrack
python3 -m venv .venv-reader
source .venv-reader/bin/activate
pip install -r reader_service/requirements.txt
export EDUTRACK_API_URL=http://localhost:8000
export EDUTRACK_DEVICE_CODE=CODIGO_DE_UN_DISPOSITIVO_EXISTENTE
export EDUTRACK_INGESTA_TOKEN=EL_MISMO_INGESTA_TOKEN_DEL_BACKEND
python reader_service/bluetooth_receiver.py --port /dev/rfcomm0 --baud 9600
```

El backend se inicia por separado desde `backend` con `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Si corre en otra computadora, asigna su dirección accesible a `EDUTRACK_API_URL`. El receptor reintenta abrir RFCOMM cada tres segundos tras una desconexión. Para confirmar el flujo, una lectura autenticada aparece en los eventos del lector; una tarjeta desconocida devuelve `TARJETA_NO_REGISTRADA`. La rotación requiere actualizar el mismo secreto en el backend y todos los receptores; el anterior deja de aceptarse.

## Probar asistencia y asociación

Con el backend, el HC-05 y `bluetooth_receiver.py` activos, presenta una tarjeta registrada para comprobar el registro habitual de asistencia. Para asociar una tarjeta nueva, abre **Alumnos → Asociar tarjeta**; la ventana debe indicar que está leyendo. Presenta la tarjeta al RC522 y espera el mensaje de asociación correcta. El UID de esa captura se guarda en `"Credenciales_rfid"` y no se registra como asistencia. Al cerrar o cancelar la ventana, las lecturas vuelven al procesamiento habitual.

El endpoint administrativo `GET /rfid/reader/status` muestra la conexión y si hay una captura activa. `GET /rfid/reader/events?after=0` muestra resultados de lecturas normales. El firmware debe emitir UIDs de 8, 14 o 20 caracteres hexadecimales.
