"""Modelos de entrada de la API de autenticación y vinculación."""

from datetime import date

from pydantic import BaseModel, EmailStr, Field, model_validator


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


class CambiarPasswordEntrada(BaseModel):
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


class EstudianteCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=200)
    matricula: str = Field(min_length=1, max_length=80)
    grupo: str = Field(min_length=1, max_length=80)
    correo_institucional: EmailStr | None = None


class EstudianteActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=200)
    matricula: str | None = Field(default=None, min_length=1, max_length=80)
    grupo: str | None = Field(default=None, min_length=1, max_length=80)
    correo_institucional: EmailStr | None = None


class TarjetaCrear(BaseModel):
    uid: str = Field(min_length=8, max_length=20, pattern="^[0-9A-Fa-f]+$")
    id_estudiante: int = Field(gt=0)
    propietario: str | None = Field(default=None, max_length=120)
    vigencia_inicio: date | None = None
    vigencia_termino: date | None = None

    @model_validator(mode="after")
    def validar_vigencia(self):
        if self.vigencia_inicio and self.vigencia_termino and self.vigencia_termino < self.vigencia_inicio:
            raise ValueError("La vigencia final debe ser igual o posterior a la inicial.")
        if len(self.uid) not in (8, 14, 20):
            raise ValueError("El UID debe tener 4, 7 o 10 bytes en hexadecimal.")
        return self


class TutorActualizar(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    telefono: str | None = Field(default=None, max_length=30)


class PreferenciasTutor(BaseModel):
    notificaciones_habilitadas: bool


class PlantelActualizar(BaseModel):
    nombre: str = Field(min_length=2, max_length=200)
    direccion: str = Field(min_length=2, max_length=250)
    telefono: str = Field(min_length=5, max_length=30)
    correo: EmailStr


class HorarioCrear(BaseModel):
    dia_semana: str = Field(min_length=3, max_length=20)
    grupo: str = Field(min_length=1, max_length=80)
    hora_de_entrada: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")
    hora_de_salida: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")
    tolerancia: int = Field(default=0, ge=0, le=240)

    @model_validator(mode="after")
    def validar_horas(self):
        if self.hora_de_entrada >= self.hora_de_salida:
            raise ValueError("La hora de salida debe ser posterior a la hora de entrada.")
        return self


class HorarioActualizar(BaseModel):
    dia_semana: str | None = Field(default=None, min_length=3, max_length=20)
    grupo: str | None = Field(default=None, min_length=1, max_length=80)
    hora_de_entrada: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")
    hora_de_salida: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")
    tolerancia: int | None = Field(default=None, ge=0, le=240)

    @model_validator(mode="after")
    def validar_horas(self):
        if self.hora_de_entrada and self.hora_de_salida and self.hora_de_entrada >= self.hora_de_salida:
            raise ValueError("La hora de salida debe ser posterior a la hora de entrada.")
        return self


class LecturaRFIDEntrada(BaseModel):
    uid: str = Field(min_length=8, max_length=20, pattern="^[0-9A-Fa-f]+$")
    codigo_dispositivo: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def validar_uid(self):
        if len(self.uid) not in (8, 14, 20):
            raise ValueError("UID hexadecimal no soportado.")
        return self
