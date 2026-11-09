import { HttpErrorResponse } from '@angular/common/http';

/** Extrae un mensaje legible del error devuelto por el backend. */
export function mensajeDeError(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) {
    return 'Ocurrió un error inesperado. Intenta de nuevo.';
  }
  if (error.status === 0) {
    return 'No se pudo contactar con el servidor. Verifica que FastAPI esté en ejecución.';
  }

  const detalle = error.error?.detail ?? error.error;

  if (typeof detalle === 'string') {
    return detalle;
  }
  if (detalle && typeof detalle === 'object') {
    if (typeof detalle.msg === 'string') {
      return detalle.msg;
    }
    if (typeof detalle.error_description === 'string') {
      return detalle.error_description;
    }
    if (typeof detalle.message === 'string') {
      return detalle.message;
    }
  }
  return 'Ocurrió un error inesperado. Intenta de nuevo.';
}
