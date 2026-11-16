# Arquitectura de EduTrack

\`\`\`text
RC522 --SPI--> Arduino UNO --USB Serial--> FastAPI --> PostgreSQL/Supabase
                                            ^
Angular standalone -------------------------|
\`\`\`

FastAPI administra una instancia persistente de backend/app/rfid_reader.py, iniciada y cerrada con el ciclo de vida de la aplicación. Un hilo detecta los puertos disponibles, identifica el firmware con PING, lee las respuestas seriales sin bloquear las rutas HTTP y recupera la conexión al perder USB. Para asociar una tarjeta, Angular solicita POST /rfid/reader/associate/{id_estudiante}; el endpoint captura un UID, valida 4/7/10 bytes, comprueba el estudiante y escribe en la tabla existente Credenciales_rfid. El identificador del alumno viaja ligado a esa única solicitud de captura.

El firmware reader_service/arduino/lector_rfid.ino implementa protocolo ASCII v1 a 9600 baudios: PING, READ, CANCEL; respuestas READY:EDUTRACK_RFID:1:OK, CAPTURING, UID: <HEX>, CANCELLED y errores ERROR:RC522_INIT. El UID solo se reporta durante una captura solicitada.

GET /rfid/reader/status informa conectividad al frontend. Las rutas de estado, asociación y cancelación requieren una sesión administrativa verificada. La ingesta RFID existente POST /rfid/lecturas y su lógica de asistencia permanecen disponibles; el servicio Python antiguo también abre USB serial y no se debe iniciar junto con FastAPI. Consulta HARDWARE.md para instalación y pruebas físicas.

La conexión USB requiere que FastAPI se ejecute en la computadora conectada al Arduino. La aplicación Angular debe usar la URL local de esa instancia durante la operación del lector.
