# Servicios cloud y despliegue

Servicios de EduTrack: Supabase (PostgreSQL y Auth), Render (FastAPI), Vercel (Angular), Resend (correo de aplicación) y Firebase Cloud Messaging (push). La Raspberry Pi conserva la cola durable SQLite; no se necesita almacenamiento cloud para esa cola.

La integración FCM queda inactiva hasta que se configuren credenciales. FastAPI inicia sin Firebase; los endpoints push solo se activan para tutores autenticados y dispositivos registrados. No se envían notificaciones de prueba automáticamente.

## Variables

Completa `backend/.env.example` para desarrollo. No reemplaces ni compartas `backend/.env`. Configura los secretos en Render y las variables públicas web en Vercel:

| Variables | Plataforma | Uso |
| --- | --- | --- |
| `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD` | Render | PostgreSQL de Supabase. |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | Render | Validación de sesión con Supabase Auth. No requiere `service_role`. |
| `CORS_ORIGINS` | Render | Dominios del frontend permitidos. |
| `RFID_INGEST_TOKEN` | Render y Raspberry Pi | Autentica la ingesta del lector existente. |
| `RESEND_API_KEY`, `EMAIL_FROM` | Render | Correo iniciado por EduTrack. |
| `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY` | Render/backend local | Cuenta de servicio privada para Firebase Admin. La clave admite saltos de línea o `\\n` literales. |
| `EDUTRACK_API_URL` | Vercel, build | URL pública de FastAPI. |
| `FIREBASE_WEB_API_KEY`, `FIREBASE_WEB_AUTH_DOMAIN`, `FIREBASE_WEB_PROJECT_ID`, `FIREBASE_WEB_STORAGE_BUCKET`, `FIREBASE_WEB_MESSAGING_SENDER_ID`, `FIREBASE_WEB_APP_ID`, `FIREBASE_WEB_VAPID_KEY` | Vercel, build | Configuración pública de Firebase Web y VAPID; se publica en runtime-config.js. |

Firebase Web config y VAPID son valores públicos. La clave privada de la cuenta de servicio no es pública y solo se configura en Render/backend. Nunca subas el JSON de servicio ni pegues claves privadas en Angular, Vercel, GitHub o este documento. No agregues `SUPABASE_SERVICE_ROLE_KEY` al frontend.

## Preparación manual de Firebase

1. En [Firebase Console](https://console.firebase.google.com/), crea un proyecto o selecciona el proyecto existente. Configura el mismo Project ID que usará Render.
2. En **Project settings → General → Your apps**, agrega una aplicación Web y copia su configuración pública (`apiKey`, `authDomain`, `projectId`, `storageBucket`, `messagingSenderId`, `appId`). Registra los campos correspondientes como variables `FIREBASE_WEB_*` en Vercel.
3. En Firebase Console abre **Messaging** y habilita/termina la configuración de Firebase Cloud Messaging para el proyecto. Si la consola pide habilitar la API de registro FCM, actívala en el proyecto Google Cloud asociado.
4. En **Project settings → Cloud Messaging → Web configuration**, genera un par de claves Web Push. Copia la clave pública en `FIREBASE_WEB_VAPID_KEY`; nunca publiques la clave privada VAPID.
5. En **Project settings → Service accounts**, crea una clave de cuenta de servicio. Guarda el JSON fuera del repositorio. Copia su `project_id`, `client_email` y `private_key` en `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL` y `FIREBASE_PRIVATE_KEY` de Render. En Render conserva los saltos de línea o conviértelos en `\\n`. No añadas el archivo JSON al proyecto.
6. Redepliega Vercel y Render. El build de Vercel compone `public/runtime-config.js`; esos datos web son públicos por diseño. Usa HTTPS y concede al navegador permiso de notificación.

## Supabase y SQL pendiente

El repo muestra `Tutores.auth_user_id`, `Estudiante_Tutor (Id_Estudiante, Id_Tutor, Autorizado)` y la migración existente `Preferencias_Tutor`, pero no contiene el esquema completo del proyecto Supabase. Revisa en Supabase que no exista ya una tabla equivalente antes de aprobar o ejecutar [la propuesta SQL de dispositivos FCM](backend/migrations/PROPUESTA_dispositivos_fcm.sql).

La propuesta crea una tabla aditiva por usuario autenticado con varios tokens por tutor, token único, fecha de actualización, marca activa y borrado en cascada al eliminar Auth user. No cambia tablas existentes, no crea políticas de acceso cliente y no se ha ejecutado. FastAPI vincula tokens al usuario de `Authorization: Bearer` validado, nunca a un UID enviado por el navegador.

Hasta aprobar y aplicar esa tabla, el backend devuelve 503 al registrar dispositivos; el resto de EduTrack sigue funcionando y FCM permanece sin destinatarios. Los tutores se resuelven desde la relación autorizada del estudiante y solo los dispositivos activos con preferencia habilitada reciben notificaciones. Los tokens inválidos que FCM devuelve se desactivan.

## Notificaciones contempladas

- Entrada registrada y entrada con retardo: se genera al guardar una nueva entrada RFID; el retardo usa el horario del grupo, día y tolerancia configurados.
- Inasistencia: existe el emisor reutilizable `notificar_tutores_estudiante(...)`; no hay un proceso de cierre de jornada que determine ausencias, así que no se inventa ni se activa un horario de envío.
- Avisos administrativos: `notificar_administradores(...)` limita destinatarios a cuentas que ya figuren en `Administradores` y tengan dispositivo activo.

Las lecturas duplicadas y salidas no generan push de entrada. La preferencia de notificaciones del tutor se consulta antes de enviar. No se hace envío masivo indiscriminado ni se incluye información sensible adicional del estudiante en el payload.

## Registro de un dispositivo

Una vez aplicada la propuesta SQL, entra como tutor verificado, abre **Configuración de mi cuenta** y activa **Notificaciones habilitadas**. El navegador solicita permiso desde esa acción del usuario, obtiene un token FCM con el service worker raíz y lo envía a `PUT /notificaciones/dispositivo` con el JWT de sesión. Si el permiso fue denegado, habilítalo en los permisos del sitio. Al desactivar la preferencia se intenta desactivar el token del navegador en el backend. Se puede registrar más de un dispositivo por tutor.

El service worker `public/firebase-messaging-sw.js` recibe los mensajes en segundo plano. Con la aplicación abierta, `PushNotificationsService.mensajeRecibido` expone el mensaje recibido para que la interfaz lo presente; el proyecto puede conectar esa señal a su sistema visual sin cambiar el layout actual.

## Notificación de prueba controlada

No existe endpoint público para enviar mensajes arbitrarios. Después de configurar todo y aplicar la SQL:

1. Usa un proyecto Firebase de desarrollo, una cuenta tutor de prueba y un estudiante de prueba vinculado solo a esa cuenta.
2. Habilita notificaciones desde la configuración del tutor y confirma `PUT /notificaciones/dispositivo` en el log/respuesta.
3. Registra una entrada con la tarjeta del estudiante de prueba. Verifica en el navegador la notificación (foreground/background) y en Render que no hubo errores.
4. Para comprobar el retardo, ajusta en datos de prueba el horario y tolerancia de ese grupo y repite con un estudiante de prueba.

No ejecutes esta prueba con tutores o estudiantes reales. Las ausencias requieren definir y aprobar la hora de cierre de jornada antes de programar un job.

## Render y Vercel

Render usa `render.yaml`, raíz `backend`, `pip install -r requirements.txt`, Uvicorn y `/health`. Completa variables PostgreSQL, Supabase, CORS, RFID, Resend y Firebase según aplique. `/health` no verifica credenciales opcionales.

Vercel usa `npm run build:vercel` y output `dist/EduTrack/browser`; configura `EDUTRACK_API_URL` y las siete variables públicas `FIREBASE_WEB_*` en Preview/Production. El build requiere `EDUTRACK_API_URL`; Firebase puede omitirse para dejar push inactivo.

## Supabase Auth y correo

Supabase Auth conserva login, OTP, refresh y validación de sesión; sus plantillas SMTP se configuran en el panel Supabase. Resend se usa por separado para mensajes iniciados por la app. Consulta [backend/CONFIGURAR_GMAIL_SUPABASE.md](backend/CONFIGURAR_GMAIL_SUPABASE.md) si el SMTP de Supabase usa Gmail.
