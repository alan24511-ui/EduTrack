"""Inicialización opcional de Firebase Admin y envío dirigido a tutores."""

from functools import lru_cache
import logging

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    from firebase_admin.exceptions import FirebaseError
except ImportError:  # Mantiene el backend operativo ante una instalación opcional incompleta.
    firebase_admin = None
    credentials = messaging = None
    FirebaseError = Exception

from app.config import obtener_settings
from app.database import obtener_conexion

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def obtener_app_firebase():
    """Crea la app solo si están las credenciales; Firebase nunca bloquea el arranque."""
    if firebase_admin is None:
        logger.warning("Firebase Admin SDK no está instalado; push permanece desactivado.")
        return None
    settings = obtener_settings()
    if not all((settings.firebase_project_id, settings.firebase_client_email, settings.firebase_private_key)):
        return None
    try:
        try:
            return firebase_admin.get_app()
        except ValueError:
            pass
        private_key = settings.firebase_private_key.replace("\\n", "\n")
        credencial = credentials.Certificate({
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "client_email": settings.firebase_client_email,
            "private_key": private_key,
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        return firebase_admin.initialize_app(credencial, {"projectId": settings.firebase_project_id})
    except Exception as error:
        logger.error("No se pudo inicializar Firebase Admin (%s).", type(error).__name__)
        return None


def firebase_configurado() -> bool:
    return obtener_app_firebase() is not None


def enviar_a_tokens(tokens: list[str], titulo: str, cuerpo: str, datos: dict[str, str] | None = None) -> int:
    """Envía a los tokens indicados y desactiva los que FCM ya no reconoce."""
    app = obtener_app_firebase()
    if not app or not tokens:
        return 0
    enviados = 0
    for inicio in range(0, len(tokens), 500):
        lote = tokens[inicio:inicio + 500]
        try:
            respuesta = messaging.send_each_for_multicast(
                messaging.MulticastMessage(
                    tokens=lote,
                    notification=messaging.Notification(title=titulo, body=cuerpo),
                    data=datos or {},
                    webpush=messaging.WebpushConfig(
                        notification=messaging.WebpushNotification(title=titulo, body=cuerpo)
                    ),
                ),
                app=app,
            )
            enviados += respuesta.success_count
            invalidos = [
                token for token, resultado in zip(lote, respuesta.responses)
                if not resultado.success and getattr(resultado.exception, "code", "") in {
                    "registration-token-not-registered", "invalid-registration-token"
                }
            ]
            if invalidos:
                with obtener_conexion() as conn, conn.cursor() as cur:
                    cur.execute(
                        'UPDATE "Dispositivos_FCM" SET activo=FALSE, updated_at=now() WHERE token = ANY(%s)',
                        (invalidos,),
                    )
        except FirebaseError as error:
            logger.warning("Firebase rechazó el envío (%s).", type(error).__name__)
        except Exception as error:
            logger.warning("No se pudo completar el envío FCM (%s).", type(error).__name__)
    return enviados


def notificar_tutores_estudiante(
    id_estudiante: int, categoria: str, titulo: str, cuerpo: str, evento_id: str | None = None
) -> int:
    """Dirige una notificación a tutores autorizados vinculados con ese estudiante."""
    if not firebase_configurado():
        return 0
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(
                'SELECT d.token FROM "Dispositivos_FCM" d '
                'JOIN "Tutores" t ON t.auth_user_id=d.auth_user_id '
                'JOIN "Estudiante_Tutor" et ON et."Id_Tutor"=t."Id_Tutor" '
                'LEFT JOIN "Preferencias_Tutor" p ON p.auth_user_id=t.auth_user_id '
                'WHERE et."Id_Estudiante"=%s AND et."Autorizado"=TRUE AND d.activo=TRUE '
                'AND COALESCE(p.notificaciones_habilitadas, TRUE)=TRUE',
                (id_estudiante,),
            )
            tokens = list(dict.fromkeys(row[0] for row in cur.fetchall()))
        return enviar_a_tokens(tokens, titulo, cuerpo, {"categoria": categoria, "eventoId": evento_id or ""})
    except Exception as error:
        logger.warning("No se pudieron resolver destinatarios FCM (%s).", type(error).__name__)
        return 0


def notificar_administradores(titulo: str, cuerpo: str, evento_id: str | None = None) -> int:
    """Notifica cuentas administrativas registradas; nunca envía a todos los tutores."""
    if not firebase_configurado():
        return 0
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(
                'SELECT d.token FROM "Dispositivos_FCM" d '
                'JOIN "Administradores" a ON a.auth_user_id=d.auth_user_id WHERE d.activo=TRUE'
            )
            tokens = list(dict.fromkeys(row[0] for row in cur.fetchall()))
        return enviar_a_tokens(tokens, titulo, cuerpo, {"categoria": "aviso_administrativo", "eventoId": evento_id or ""})
    except Exception as error:
        logger.warning("No se pudieron resolver administradores FCM (%s).", type(error).__name__)
        return 0
