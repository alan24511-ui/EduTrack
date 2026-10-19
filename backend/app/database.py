
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv



# Carga el archivo backend/.env sin depender de la carpeta
# desde la que se ejecute FastAPI.
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)


def obtener_conexion():
    """Abre una conexión con la base de datos PostgreSQL."""
    return psycopg.connect(
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=int(os.getenv("DATABASE_PORT", "5432")),
        dbname=os.getenv("DATABASE_NAME", "edutrack"),
        user=os.getenv("DATABASE_USER", "postgres"),
        password=os.getenv("DATABASE_PASSWORD", ""),
        connect_timeout=5,
    )
