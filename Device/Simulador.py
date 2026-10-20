
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# Dirección de la API local de EduTrack.
API_URL = "http://127.0.0.1:8000/device/scan"


# UID ficticios para probar las respuestas de la API.
UIDS_DE_PRUEBA = [
    ("A1B2C3D4", "conocida"),
    ("DEADBEEF", "desconocida"),
]


def enviar_uid(uid):
    datos = json.dumps({"uid": uid}).encode("utf-8")

    solicitud = Request(
        API_URL,
        data=datos,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(solicitud, timeout=5) as respuesta:
            codigo = respuesta.status
            cuerpo = json.loads(
                respuesta.read().decode("utf-8")
            )

    except HTTPError as error:
        # FastAPI también devuelve respuestas HTTP de error,
        # por ejemplo, 404 cuando la tarjeta no está registrada.
        codigo = error.code

        try:
            cuerpo = json.loads(
                error.read().decode("utf-8")
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            cuerpo = {"detail": "La API devolvió un error."}

    except URLError as error:
        print(f"ERROR DE CONEXIÓN: {error.reason}")
        print("Comprueba que FastAPI esté ejecutándose.")
        return False

    print(f"\nUID enviado: {uid}")
    print(f"Código HTTP: {codigo}")
    print(
        "Respuesta:",
        json.dumps(cuerpo, indent=2, ensure_ascii=False),
    )

    # Comprobar el resultado esperado para cada prueba.
    if uid == "A1B2C3D4" and codigo == 200:
        if cuerpo.get("status") == "recognized":
            print("PRUEBA CORRECTA: tarjeta reconocida.")
            return True

    elif uid == "DEADBEEF" and codigo == 404:
        detalle = cuerpo.get("detail", {})

        if (
            isinstance(detalle, dict)
            and detalle.get("status") == "unknown"
        ):
            print("PRUEBA CORRECTA: tarjeta desconocida.")
            return True

    print("PRUEBA FALLIDA: respuesta inesperada.")
    return False


if __name__ == "__main__":
    resultados = []

    for uid, tipo in UIDS_DE_PRUEBA:
        print(f"\n--- Prueba de tarjeta {tipo} ---")
        resultados.append(enviar_uid(uid))

    exitosas = sum(resultados)

    print("\n================================")
    print(f"RESULTADO: {exitosas}/{len(resultados)} pruebas correctas")
    print("================================")

    if exitosas != len(resultados):
        raise SystemExit(1)
