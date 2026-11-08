"""Modelos de entrada de la API de autenticación y vinculación."""

from pydantic import BaseModel, EmailStr, Field


class RegistroTutorEntrada(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    correo: EmailStr
    password: str = Field(min_length=8, max_length=72)


class VerificacionOTPEntrada(BaseModel):
    correo: EmailStr
    token: str = Field(min_length=4, max_length=10)


class CorreoEntrada(BaseModel):
    correo: EmailStr


class ReenvioOTPEntrada(BaseModel):
    correo: EmailStr
    tipo: str = Field(pattern="^(signup|recovery)$")


class RenovacionSesionEntrada(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class RecuperacionPasswordEntrada(BaseModel):
    correo: EmailStr
    token: str = Field(min_length=4, max_length=10)
    nueva_password: str = Field(min_length=8, max_length=72)


class LoginEntrada(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=1, max_length=72)


class GenerarCodigoEntrada(BaseModel):
    matricula: str = Field(min_length=1, max_length=40)


class ConsultaCodigoEntrada(BaseModel):
    codigo: str = Field(min_length=4, max_length=32)


class ConfirmacionVinculacionEntrada(BaseModel):
    codigo: str = Field(min_length=4, max_length=32)
    parentesco: str = Field(min_length=2, max_length=60)
