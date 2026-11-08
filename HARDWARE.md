# Hardware y servicio del lector RFID

## Material y conexiones

Arquitectura soportada: RC522 → Arduino Uno → USB serial → servicio Python en computadora → FastAPI. No se utiliza Raspberry Pi.

| RC522 | Arduino Uno |
|---|---|
| SDA / SS | D10 |
| SCK | D13 |
| MOSI | D11 |
| MISO | D12 |
| RST | D9 |
| GND | GND |
| 3.3V | 3.3V |

El módulo RC522 es de 3.3 V y sus entradas no deben recibir directamente señales de 5 V del Uno. Usa un convertidor de nivel lógico bidireccional o adaptación adecuada en las líneas Uno→RC522 (SS, SCK, MOSI y RST); conecta alimentación a 3.3 V estable. No alimentes el RC522 desde 5 V.

## Firmware

Abre `firmware/arduino_rc522/arduino_rc522.ino` en Arduino IDE, instala la biblioteca **MFRC522** de Miguel Balboa, selecciona Arduino Uno y el puerto correcto, y carga el sketch. El protocolo es ASCII, una línea terminada en LF: `UID:<UID hexadecimal uppercase>\n`. No se agregan separadores entre bytes; se conservan ceros iniciales. Velocidad: 115200. El firmware limita reenvíos del mismo UID a uno cada 1.8 segundos.

## Servicio Python en Fedora/Linux

```bash
cd reader_service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python reader_service.py --port /dev/ttyACM0 --baud 115200 \
  --endpoint http://localhost:8000/rfid/lecturas
```

`--port`, `--baud`, `--endpoint` y `--cooldown` también se pueden configurar con `EDUTRACK_SERIAL_PORT`, `EDUTRACK_SERIAL_BAUD`, `EDUTRACK_RFID_ENDPOINT` y `--cooldown`. Si se omite el puerto, se selecciona solo cuando hay exactamente un dispositivo serial; en otro caso se solicita especificarlo. En Fedora, el usuario debe tener permiso de acceso al dispositivo (grupo `dialout` u otro grupo asignado por la distribución); vuelve a iniciar sesión después de cambiar grupos.

El servicio valida UID de 4, 7 o 10 bytes, evita reenvíos consecutivos dentro del cooldown, reporta desconexiones y reintenta. Los errores HTTP/serial se registran sin imprimir cuerpos, UID, URL ni credenciales. No tiene conexión a Supabase ni secretos privilegiados.

## Prueba de protocolo vs. hardware

`python -m unittest` en `reader_service` prueba líneas representativas simuladas. Esa prueba no confirma lectura física. La operación HTTP real está bloqueada hasta que exista y se configure el endpoint FastAPI seguro de ingestión. El sistema no debe considerarse verificado con el lector hasta probar cableado, niveles, puerto, lecturas reales y respuesta del backend.
