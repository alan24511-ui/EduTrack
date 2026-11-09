# Configurar Gmail para los códigos de EduTrack

EduTrack usa **Supabase Auth** para crear, enviar y validar los códigos OTP de registro y recuperación. FastAPI solo solicita esas operaciones a Supabase. Por eso, en un proyecto Supabase alojado, el SMTP se configura en el panel de Supabase y no en `backend/.env`.

## Valores para SMTP de Gmail

1. En la cuenta remitente, activa la verificación en dos pasos y crea una contraseña de aplicación. Usa esa contraseña, nunca la contraseña normal de Gmail.
2. En Supabase abre **Authentication → SMTP Settings**, habilita el proveedor SMTP personalizado y configura:

   | Campo | Valor |
   | --- | --- |
   | Host | `smtp.gmail.com` |
   | Port | `587` |
   | Username | La dirección Gmail remitente completa |
   | Password | La contraseña de aplicación de Google |
   | Sender email | La misma dirección Gmail |
   | Sender name | `EduTrack` |

3. Guarda la configuración y revisa **Authentication → Email Templates**. Las plantillas de registro y recuperación deben incluir el token OTP (`{{ .Token }}`) porque las pantallas de EduTrack piden un código; no cambies a enlaces mágicos sin adaptar el flujo.
4. Verifica registro, reenvío de código y recuperación con una cuenta de prueba. Revisa también los logs de Auth de Supabase si un correo no llega.

Google requiere autenticación SMTP cifrada y documenta el puerto 587 para TLS/STARTTLS. La contraseña de aplicación requiere verificación en dos pasos y puede no estar disponible en algunas cuentas administradas. Revisa las políticas y límites vigentes de Google antes de usar Gmail para tráfico real.

## Secretos y entorno

- No agregues la contraseña de aplicación a Angular, al repositorio ni a `backend/.env` para Supabase alojado.
- El archivo `backend/.env.example` solo señala dónde se configura SMTP; no contiene credenciales.
- Si se usa una instancia local o autohospedada de Supabase, configura SMTP en el servicio Auth de esa instancia y guarda sus secretos en el gestor de secretos del despliegue.
- El OTP continúa generándose y validándose en Supabase Auth; esta guía no crea códigos paralelos ni tablas adicionales.
