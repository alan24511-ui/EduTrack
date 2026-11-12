
"""Inicialización de Firebase Admin y envío dirigido de notificaciones."""

from functools import lru_cache
from pathlib import Path
import logging

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    from firebase_admin.exceptions import FirebaseError
except ImportError:
    # Mantiene el backend operativo si Firebase Admin no está instalado.
    firebase_admin = None
    credentials = messaging = None
    FirebaseError = Exception

from app.config import obtener_settings
from app.database import obtener_conexion

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def obtener_app_firebase():
    """Inicializa Firebase Admin usando un archivo de credenciales protegido."""

    if firebase_admin is None:
        logger.warning(
            "Firebase Admin SDK no está instalado; push permanece desactivado."
        )
        return None

    settings = obtener_settings()

    try:
        # Evita inicializar Firebase más de una vez.
        try:
            return firebase_admin.get_app()
        except ValueError:
            pass

        # Busca el archivo JSON fuera del repositorio.
        ruta_credenciales = Path(
            settings.firebase_service_account_path
        ).expanduser()

        if ruta_credenciales.is_file():
            credencial = credentials.Certificate(str(ruta_credenciales))

        elif all((
            settings.firebase_project_id,
            settings.firebase_client_email,
            settings.firebase_private_key,
        )):
            # Compatibilidad con despliegues que utilicen variables de entorno.
            credencial = credentials.Certificate({
                "type": "service_account",
                "project_id": settings.firebase_project_id,
                "client_email": settings.firebase_client_email,
                "private_key": settings.firebase_private_key.replace("\\n", "\n"),
                "token_uri": "https://oauth2.googleapis.com/token",
            })

        else:
            logger.warning(
                "No se encontraron credenciales para Firebase Admin."
            )
            return None

        project_id = (
            settings.firebase_project_id
            or credencial.project_id
        )

        return firebase_admin.initialize_app(
            credencial,
            {"projectId": project_id},
        )

    except Exception as error:
        logger.error(
            "No se pudo inicializar Firebase Admin (%s).",
            type(error).__name__,
        )
        return None


def firebase_configurado() -> bool:
    """Indica si Firebase Admin pudo inicializarse."""
    return obtener_app_firebase() is not None


def enviar_a_tokens(
    tokens: list[str],
    titulo: str,
    cuerpo: str,
    datos: dict[str, str] | None = None,
) -> int:
    """Envía notificaciones y desactiva los tokens que FCM ya no reconoce."""

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
                    notification=messaging.Notification(
                        title=titulo,
                        body=cuerpo,
                    ),
                    data=datos or {},
                    webpush=messaging.WebpushConfig(
                        notification=messaging.WebpushNotification(
                            title=titulo,
                            body=cuerpo,
                        )
                    ),
                ),
                app=app,
            )

            enviados += respuesta.success_count

            # Identifica tokens inválidos o eliminados.
            invalidos = [
                token
                for token, resultado in zip(lote, respuesta.responses)
                if not resultado.success
                and getattr(resultado.exception, "code", "") in {
                    "messaging/registration-token-not-registered",
                    "messaging/invalid-registration-token",
                    "registration-token-not-registered",
                    "invalid-registration-token",
                }
            ]

            # Desactiva los tokens que ya no son válidos.
            if invalidos:
                with obtener_conexion() as conn, conn.cursor() as cur:
                    cur.execute(
                        'UPDATE "Dispositivos_FCM" '
                        'SET activo=FALSE, updated_at=now() '
                        'WHERE token = ANY(%s)',
                        (invalidos,),
                    )

        except FirebaseError as error:
            logger.warning(
                "Firebase rechazó el envío (%s).",
                type(error).__name__,
            )

        except Exception as error:
            logger.warning(
                "No se pudo completar el envío FCM (%s).",
                type(error).__name__,
            )

    return enviados


def notificar_tutores_estudiante(
    id_estudiante: int,
    categoria: str,
    titulo: str,
    cuerpo: str,
    evento_id: str | None = None,
) -> int:
    """Notifica a los tutores autorizados vinculados con un estudiante."""

    if not firebase_configurado():
        return 0

    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(
                'SELECT d.token FROM "Dispositivos_FCM" d '
                'JOIN "Tutores" t ON t.auth_user_id=d.auth_user_id '
                'JOIN "Estudiante_Tutor" et '
                'ON et."Id_Tutor"=t."Id_Tutor" '
                'LEFT JOIN "Preferencias_Tutor" p '
                'ON p.auth_user_id=t.auth_user_id '
                'WHERE et."Id_Estudiante"=%s '
                'AND et."Autorizado"=TRUE '
                'AND d.activo=TRUE '
                'AND COALESCE(p.notificaciones_habilitadas, TRUE)=TRUE',
                (id_estudiante,),
            )

            tokens = list(
                dict.fromkeys(row[0] for row in cur.fetchall())
            )

        return enviar_a_tokens(
            tokens,
            titulo,
            cuerpo,
            {
                "categoria": categoria,
                "eventoId": evento_id or "",
            },
        )

    except Exception as error:
        logger.warning(
            "No se pudieron resolver destinatarios FCM (%s).",
            type(error).__name__,
        )
        return 0


def notificar_administradores(
    titulo: str,
    cuerpo: str,
    evento_id: str | None = None,
) -> int:
    """Notifica cuentas administrativas registradas."""

    if not firebase_configurado():
        return 0

    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(
                'SELECT d.token FROM "Dispositivos_FCM" d '
                'JOIN "Administradores" a '
                'ON a.auth_user_id=d.auth_user_id '
                'WHERE d.activo=TRUE'
            )

            tokens = list(
                dict.fromkeys(row[0] for row in cur.fetchall())
            )

        return enviar_a_tokens(
            tokens,
            titulo,
            cuerpo,
            {
                "categoria": "aviso_administrativo",
                "eventoId": evento_id or "",
            },
        )

    except Exception as error:
        logger.warning(
            "No se pudieron resolver administradores FCM (%s).",
            type(error).__name__,
        )
        return 0
