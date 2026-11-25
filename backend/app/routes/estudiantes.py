"""Consulta, administración e importación segura de estudiantes."""

import csv
import io
import re
import unicodedata
import zipfile
from xml.etree import ElementTree

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from psycopg import Error as PsycopgError

from app.database import obtener_conexion
from app.schemas import EstudianteActualizar, EstudianteCrear
from app.security import obtener_rol, usuario_administrador, usuario_verificado

router = APIRouter(prefix="/estudiantes", tags=["Estudiantes"])
MAX_ARCHIVO_IMPORTACION = 5 * 1024 * 1024


def _clave_encabezado(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", valor.strip().lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _leer_xlsx(contenido: bytes) -> list[list[str]]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    with zipfile.ZipFile(io.BytesIO(contenido)) as libro:
        shared = []
        if "xl/sharedStrings.xml" in libro.namelist():
            raiz = ElementTree.fromstring(libro.read("xl/sharedStrings.xml"))
            shared = ["".join(n.text or "" for n in item.findall(".//m:t", ns)) for item in raiz.findall("m:si", ns)]
        hoja = ElementTree.fromstring(libro.read("xl/worksheets/sheet1.xml"))
        filas = []
        for fila in hoja.findall(".//m:sheetData/m:row", ns):
            celdas = []
            for celda in fila.findall("m:c", ns):
                ref = celda.attrib.get("r", "")
                letras = re.match(r"[A-Z]+", ref)
                columna = 0
                if letras:
                    for letra in letras.group(): columna = columna * 26 + ord(letra) - 64
                    columna -= 1
                while len(celdas) <= columna: celdas.append("")
                valor = celda.find("m:v", ns)
                inline = celda.find("m:is", ns)
                texto = "" if valor is None else valor.text or ""
                if celda.attrib.get("t") == "s" and texto: texto = shared[int(texto)]
                if inline is not None: texto = "".join(n.text or "" for n in inline.findall(".//m:t", ns))
                celdas[columna] = texto
            filas.append(celdas)
        return filas


def _analizar_filas(filas: list[list[str]], existentes: set[str], grupos: set[str]):
    if not filas:
        raise HTTPException(status_code=422, detail="El archivo no contiene filas.")
    encabezados = [_clave_encabezado(str(v)) for v in filas[0]]
    aliases = {"matricula": {"matricula", "identificador escolar", "id escolar"}, "nombre": {"nombre", "nombres"}, "apellidos": {"apellido", "apellidos"}, "grupo": {"grupo"}}
    indices = {campo: next((i for i, encabezado in enumerate(encabezados) if encabezado in nombres), None) for campo, nombres in aliases.items()}
    faltan = [campo for campo in ("matricula", "nombre", "grupo") if indices[campo] is None]
    if faltan: raise HTTPException(status_code=422, detail="Faltan columnas requeridas: " + ", ".join(faltan))
    vistos = set()
    salida = []
    for numero, fila in enumerate(filas[1:], start=2):
        if not any(str(v).strip() for v in fila): continue
        item = {campo: (str(fila[idx]).strip() if idx is not None and idx < len(fila) else "") for campo, idx in indices.items()}
        errores = []
        if not item["matricula"] or len(item["matricula"]) > 80: errores.append("Matrícula obligatoria (máximo 80 caracteres).")
        if not item["nombre"] or len(item["nombre"]) < 2 or len(item["nombre"]) > 200: errores.append("Nombre obligatorio (2 a 200 caracteres).")
        if len(item["apellidos"]) > 200: errores.append("Apellidos: máximo 200 caracteres.")
        if not item["grupo"] or len(item["grupo"]) > 80: errores.append("Grupo obligatorio (máximo 80 caracteres).")
        clave = item["matricula"].casefold()
        if clave and clave in existentes: errores.append("La matrícula ya existe.")
        elif clave and clave in vistos: errores.append("La matrícula está duplicada en el archivo.")
        if clave: vistos.add(clave)
        if item["grupo"] and item["grupo"].casefold() not in grupos: errores.append("El grupo no existe en EduTrack.")
        salida.append({"fila": numero, **item, "valida": not errores, "errores": errores})
    return salida


def _validar_archivo(nombre: str, contenido: bytes, cur):
    if len(contenido) > MAX_ARCHIVO_IMPORTACION: raise HTTPException(status_code=413, detail="El archivo supera el límite de 5 MB.")
    if nombre.lower().endswith(".csv"):
        try: filas = list(csv.reader(io.StringIO(contenido.decode("utf-8-sig"), newline="")))
        except (UnicodeDecodeError, csv.Error) as error: raise HTTPException(status_code=422, detail="No se pudo leer el CSV UTF-8.") from error
    elif nombre.lower().endswith(".xlsx"):
        try: filas = _leer_xlsx(contenido)
        except (zipfile.BadZipFile, KeyError, ValueError, ElementTree.ParseError) as error: raise HTTPException(status_code=422, detail="El archivo XLSX no es válido o está dañado.") from error
    else: raise HTTPException(status_code=415, detail="Usa un archivo CSV o XLSX.")
    cur.execute('SELECT "Matricula" FROM "Estudiantes"')
    existentes = {str(f[0]).casefold() for f in cur.fetchall()}
    cur.execute('SELECT DISTINCT "Grupo" FROM "Estudiantes" WHERE "Grupo" IS NOT NULL AND btrim("Grupo") <> \'\'')
    grupos = {str(f[0]).casefold() for f in cur.fetchall()}
    return _analizar_filas(filas, existentes, grupos)


def _traducir_error_db(error: PsycopgError):
    if getattr(error, "sqlstate", None) == "23505":
        raise HTTPException(status_code=409, detail="La matrícula o correo ya está registrado.") from error
    if getattr(error, "sqlstate", None) == "23503":
        raise HTTPException(status_code=404, detail="El estudiante relacionado no existe.") from error
    raise HTTPException(status_code=500, detail="No fue posible completar la operación.") from error


def _estudiante(fila):
    return {"id": fila[0], "nombre": fila[1], "matricula": fila[2], "grupo": fila[3], "correoInstitucional": fila[4]}


@router.get("")
def listar_estudiantes(
    q: str = Query(default="", max_length=120),
    grupo: str | None = Query(default=None, max_length=80),
    usuario: dict = Depends(usuario_verificado),
):
    rol = obtener_rol(usuario["id"])
    filtros = []
    parametros: list = []
    if rol == "tutor":
        filtros.append('EXISTS (SELECT 1 FROM "Estudiante_Tutor" et JOIN "Tutores" t ON t."Id_Tutor"=et."Id_Tutor" WHERE et."Id_Estudiante"=e."Id_Estudiante" AND et."Autorizado"=TRUE AND t.auth_user_id=%s)')
        parametros.append(usuario["id"])
    elif rol not in {"administrador", "superadministrador"}:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    if q.strip():
        filtros.append('(e."Nombre" ILIKE %s OR e."Matricula" ILIKE %s)')
        patron = f"%{q.strip()}%"
        parametros.extend([patron, patron])
    if grupo:
        filtros.append('e."Grupo" = %s')
        parametros.append(grupo.strip())
    where = " WHERE " + " AND ".join(filtros) if filtros else ""
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('SELECT e."Id_Estudiante", e."Nombre", e."Matricula", e."Grupo", e."Correo_Institucional", EXISTS (SELECT 1 FROM "Credenciales_rfid" c WHERE c."Id_Estudiante"=e."Id_Estudiante") FROM "Estudiantes" e' + where + ' ORDER BY EXISTS (SELECT 1 FROM "Credenciales_rfid" c WHERE c."Id_Estudiante"=e."Id_Estudiante"), e."Nombre"', parametros)
            filas = cur.fetchall()
            ids = [row[0] for row in filas]
            tutores: dict[int, list[dict]] = {id_est: [] for id_est in ids}
            if ids:
                cur.execute('SELECT et."Id_Estudiante", t."Id_Tutor", t."Nombre", et."Parentesco", et."Autorizado" FROM "Estudiante_Tutor" et JOIN "Tutores" t ON t."Id_Tutor"=et."Id_Tutor" WHERE et."Id_Estudiante" = ANY(%s)', (ids,))
                for id_est, id_tutor, nombre, parentesco, autorizado in cur.fetchall():
                    tutores[id_est].append({"idTutor": id_tutor, "nombre": nombre, "parentesco": parentesco, "autorizado": autorizado})
        return [{**_estudiante(f), "tieneTarjeta": bool(f[5]), "tutores": tutores[f[0]]} for f in filas]
    except PsycopgError as error:
        _traducir_error_db(error)


@router.get("/{id_estudiante}")
def obtener_estudiante(id_estudiante: int, usuario: dict = Depends(usuario_verificado)):
    rol = obtener_rol(usuario["id"])
    consulta = 'SELECT e."Id_Estudiante", e."Nombre", e."Matricula", e."Grupo", e."Correo_Institucional" FROM "Estudiantes" e'
    params: list = [id_estudiante]
    where = ' WHERE e."Id_Estudiante"=%s'
    if rol == "tutor":
        where += ' AND EXISTS (SELECT 1 FROM "Estudiante_Tutor" et JOIN "Tutores" t ON t."Id_Tutor"=et."Id_Tutor" WHERE et."Id_Estudiante"=e."Id_Estudiante" AND et."Autorizado"=TRUE AND t.auth_user_id=%s)'
        params.append(usuario["id"])
    elif rol not in {"administrador", "superadministrador"}:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(consulta + where, params)
            fila = cur.fetchone()
        if not fila:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado.")
        return _estudiante(fila)
    except PsycopgError as error:
        _traducir_error_db(error)


@router.post("", status_code=201)
def crear_estudiante(datos: EstudianteCrear, _: dict = Depends(usuario_administrador)):
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('INSERT INTO "Estudiantes" ("Nombre", "Matricula", "Grupo", "Correo_Institucional") VALUES (%s,%s,%s,%s) RETURNING "Id_Estudiante", "Nombre", "Matricula", "Grupo", "Correo_Institucional"', (datos.nombre.strip(), datos.matricula.strip(), datos.grupo.strip(), str(datos.correo_institucional) if datos.correo_institucional else None))
            fila = cur.fetchone()
        return _estudiante(fila)
    except PsycopgError as error:
        _traducir_error_db(error)


@router.post("/importar/validar")
async def validar_importacion(archivo: UploadFile = File(...), _: dict = Depends(usuario_administrador)):
    contenido = await archivo.read(MAX_ARCHIVO_IMPORTACION + 1)
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            filas = _validar_archivo(archivo.filename or "", contenido, cur)
        return {"filas": filas, "validas": sum(1 for f in filas if f["valida"]), "conErrores": sum(1 for f in filas if not f["valida"])}
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible validar los estudiantes contra la base de datos.") from error


@router.post("/importar/confirmar")
def confirmar_importacion(filas: list[dict], _: dict = Depends(usuario_administrador)):
    if not filas or len(filas) > 5000:
        raise HTTPException(status_code=422, detail="La importación debe contener de 1 a 5000 filas.")
    datos = [["matricula", "nombre", "apellidos", "grupo"]] + [[str(f.get(campo, "")) for campo in ("matricula", "nombre", "apellidos", "grupo")] for f in filas]
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            archivo = io.StringIO(newline="")
            csv.writer(archivo).writerows(datos)
            revisadas = _validar_archivo("datos.csv", archivo.getvalue().encode("utf-8"), cur)
            importados, omitidos = 0, []
            for fila in revisadas:
                if not fila["valida"]:
                    omitidos.append({"fila": fila["fila"], "matricula": fila["matricula"], "motivo": "; ".join(fila["errores"])})
                    continue
                cur.execute("SAVEPOINT estudiante_importacion")
                try:
                    nombre_completo = f'{fila["nombre"]} {fila["apellidos"]}'.strip()
                    cur.execute('INSERT INTO "Estudiantes" ("Nombre", "Matricula", "Grupo", "Correo_Institucional") VALUES (%s,%s,%s,NULL)', (nombre_completo, fila["matricula"], fila["grupo"]))
                    cur.execute("RELEASE SAVEPOINT estudiante_importacion")
                    importados += 1
                except PsycopgError as error:
                    cur.execute("ROLLBACK TO SAVEPOINT estudiante_importacion")
                    cur.execute("RELEASE SAVEPOINT estudiante_importacion")
                    motivo = "La matrícula ya existe." if getattr(error, "sqlstate", None) == "23505" else "No fue posible guardar el estudiante."
                    omitidos.append({"fila": fila["fila"], "matricula": fila["matricula"], "motivo": motivo})
        return {"importados": importados, "omitidos": len(omitidos), "detalleOmitidos": omitidos}
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible completar la importación.") from error


@router.patch("/{id_estudiante}")
def actualizar_estudiante(id_estudiante: int, datos: EstudianteActualizar, _: dict = Depends(usuario_administrador)):
    cambios = datos.model_dump(exclude_unset=True, exclude_none=True)
    if not cambios:
        raise HTTPException(status_code=400, detail="Indica al menos un campo para actualizar.")
    columnas = {"nombre": '"Nombre"', "matricula": '"Matricula"', "grupo": '"Grupo"', "correo_institucional": '"Correo_Institucional"'}
    sets, params = [], []
    for campo, valor in cambios.items():
        sets.append(f"{columnas[campo]}=%s")
        params.append(str(valor).strip() if isinstance(valor, str) else valor)
    params.append(id_estudiante)
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('UPDATE "Estudiantes" SET ' + ",".join(sets) + ' WHERE "Id_Estudiante"=%s RETURNING "Id_Estudiante", "Nombre", "Matricula", "Grupo", "Correo_Institucional"', params)
            fila = cur.fetchone()
        if not fila:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado.")
        return _estudiante(fila)
    except PsycopgError as error:
        _traducir_error_db(error)
