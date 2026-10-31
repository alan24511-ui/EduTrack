import { HttpInterceptorFn } from '@angular/common/http';

import { environment } from '../../environments/environment';
import { CLAVE_ACCESS_TOKEN } from '../services/auth.service';

function leerToken(): string | null {
  try {
    return localStorage.getItem(CLAVE_ACCESS_TOKEN);
  } catch {
    return null;
  }
}

/**
 * Añade el token de Supabase a las peticiones dirigidas al backend de EduTrack.
 * El token nunca se envía a dominios externos.
 */
export const authInterceptor: HttpInterceptorFn = (peticion, siguiente) => {
  const token = leerToken();

  if (token && peticion.url.startsWith(environment.apiUrl)) {
    peticion = peticion.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }

  return siguiente(peticion);
};
