"""Configuración central de EduTrack (Supabase Auth y vinculación)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Reutiliza la misma ruta de .env que ya usa app/database.py para no duplicar la carga.
from app.database import ENV_PATH


class Settings(BaseSettings):
    """Variables de entorno del backend.

    Las variables de PostgreSQL siguen gestionándose en app/database.py.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Supabase ---
    supabase_url: str = ""
    supabase_anon_key: str = ""
    rfid_ingest_token: str = ""

    # --- Vinculación ---
    # Minutos que un código de vinculación permanece válido desde su creación.
    vinculacion_codigo_expiracion_minutos: int = 15
    # --- CORS ---
    cors_origins: str = "http://localhost:4200"

    @property
    def lista_cors_origins(self) -> list[str]:
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]


@lru_cache
def obtener_settings() -> Settings:
    return Settings()
