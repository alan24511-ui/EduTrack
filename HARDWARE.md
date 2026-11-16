# Asociación RFID con Arduino UNO y RC522

## Arquitectura

\`\`\`
RC522 --SPI--> Arduino UNO --USB Serial 9600--> FastAPI persistente --> PostgreSQL/Supabase
                                                        ^
Angular (Alumnos) ---------------------------------------|
\`\`\`

FastAPI se ejecuta en la computadora que tiene conectado el Arduino. Mantiene una conexión serial, detecta/reconecta el puerto y captura UID únicamente cuando un administrador solicita asociar una credencial. El proceso antiguo \`reader_service/reader_service.py\` no debe ejecutarse al mismo tiempo: también abre el puerto serial y competiría con FastAPI.

## Conexiones

Con el Arduino desconectado, conecta el RC522. El módulo trabaja a 3.3 V: no conectes VCC ni señales del RC522 a 5 V.

| RC522 | Arduino UNO |
|---|---|
| SDA / SS | D10 |
| SCK | D13 |
| MOSI | D11 |
| MISO | D12 |
| RST | D9 |
| GND | GND |
| 3.3V | 3.3V |

## Cargar el firmware

1. Instala Arduino IDE y la biblioteca **MFRC522** (Miguel Balboa) desde Library Manager. El IDE solo se necesita para cargar el firmware; no dejes abierto Serial Monitor.
2. Abre \`reader_service/arduino/lector_rfid.ino\`, selecciona Arduino Uno y el puerto USB, y carga el sketch.
3. Cierra el IDE/Serial Monitor para liberar el puerto. El firmware confirma su disponibilidad al backend automáticamente.

## Iniciar EduTrack en Fedora 44

El frontend debe apuntar al backend local para que la API tenga acceso al USB. En desarrollo, \`src/environments/environment.ts\` ya usa \`http://localhost:8000\`.

Terminal 1, backend:

\`\`\`bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
\`\`\`

Configura en \`backend/.env\` las credenciales PostgreSQL/Supabase y CORS para \`http://localhost:4200\`. El puerto se detecta automáticamente. Para fijarlo opcionalmente, define \`RFID_SERIAL_PORT=/dev/ttyACM0\`; la velocidad predeterminada es \`RFID_SERIAL_BAUD=9600\`. En Fedora, si el acceso USB se deniega, revisa el grupo propietario de \`/dev/ttyACM0\` (\`ls -l /dev/ttyACM0\`) y concede al usuario permiso para el puerto; vuelve a iniciar sesión tras cambiar grupos.

Terminal 2, Angular:

\`\`\`bash
cd /home/chato/EduTrack
npm install
npm start
\`\`\`

Abre \`http://localhost:4200\`, inicia sesión como administrador y entra a **Alumnos**. El indicador muestra la conexión. Pulsa **Asociar tarjeta** en un alumno sin tarjeta y presenta la credencial ante el RC522. Al guardar, el alumno cambia a **Tarjeta asociada** sin recargar la página. Al registrar un alumno, el aviso ofrece asociar ahora o dejarlo pendiente.

## Protocolo USB Serial v1

Todos los mensajes son líneas ASCII terminadas en \`\\n\`, a 9600 baudios:

| Dirección | Línea | Significado |
|---|---|---|
| Arduino → FastAPI | \`READY:EDUTRACK_RFID:1:OK\` | Firmware y RC522 disponibles |
| Arduino → FastAPI | \`READY:EDUTRACK_RFID:1:ERR:RC522\` / \`ERROR:RC522_INIT\` | Error de inicialización del módulo |
| FastAPI → Arduino | \`PING\` | Identificación y comprobación del lector |
| FastAPI → Arduino | \`READ\` | Armar una captura bajo demanda |
| Arduino → FastAPI | \`CAPTURING\` | Captura iniciada |
| Arduino → FastAPI | \`UID: A1B2C3D4\` | UID hexadecimal leído físicamente (4, 7 o 10 bytes) |
| FastAPI → Arduino | \`CANCEL\` | Cancelar la captura en curso |
| Arduino → FastAPI | \`CANCELLED\` | Captura cancelada |

El firmware no emite UID fuera de una captura solicitada y filtra repeticiones mientras la tarjeta permanece en el campo. FastAPI valida el formato, el alumno seleccionado y las restricciones de unicidad existentes en \`"Credenciales_rfid"\`.

## Diagnóstico y prueba física

1. Revisa \`http://localhost:8000/health\` y \`http://localhost:8000/health/db\`.
2. Consulta \`GET /rfid/reader/status\` autenticado como administrador o el indicador en Alumnos. Si no conecta, verifica cable, permisos y que ningún monitor serial u otro proceso ocupe el puerto.
3. Entra en Alumnos, abre la asociación de un alumno de prueba y presenta una tarjeta real. Confirma el UID en la respuesta, la fila nueva de \`"Credenciales_rfid"\` y el estado actualizado en el listado.
4. Prueba cancelar, desconectar/reconectar el USB y presentar un UID ya asignado. Debe cancelarse, reconectarse y rechazarse el duplicado, respectivamente.

La compilación de Angular y la sintaxis Python se pueden verificar sin hardware. La detección del Arduino, lectura UID real, reconexión USB y cableado RC522 requieren ejecutar el procedimiento con el dispositivo físico conectado.
