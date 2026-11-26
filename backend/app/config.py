"""Configuración central de EduTrack (Supabase Auth y vinculación)."""

from functools import lru_cache

from pydantic import Field
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
    rfid_debounce_seconds: int = Field(default=5, ge=1, validation_alias="RFID_DEBOUNCE_SECONDS")

    # --- Servicios opcionales ---
    firebase_project_id: str = ""
    firebase_client_email: str = ""
    firebase_private_key: str = ""
    firebase_service_account_path: str = "~/.config/edutrack/firebase-service-account.json"
    resend_api_key: str = ""
    email_from: str = ""

    # --- CORS ---
    cors_origins: str = "http://localhost:4200,https://edu-track-c4ka.vercel.app"

    @property
    def lista_cors_origins(self) -> list[str]:
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]


@lru_cache
def obtener_settings() -> Settings:
    return Settings()
