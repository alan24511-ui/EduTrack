import { HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { HttpInterceptorFn } from '@angular/common/http';
import { catchError, finalize, Observable, shareReplay, switchMap, throwError } from 'rxjs';

import { environment } from '../../environments/environment';
import { CLAVE_ACCESS_TOKEN } from '../services/auth.service';
import { CLAVE_REFRESH_TOKEN, AuthService } from '../services/auth.service';

let refreshRequest: Observable<unknown> | null = null;

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
  const auth = inject(AuthService);
  const token = leerToken();

  if (token && peticion.url.startsWith(environment.apiUrl)) {
    peticion = peticion.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }

  return siguiente(peticion).pipe(
    catchError((error: unknown) => {
      const authUrl = `${environment.apiUrl}/auth/`;
      const esAuth = peticion.url.startsWith(authUrl);
      let refreshToken: string | null = null;
      try {
        refreshToken = localStorage.getItem(CLAVE_REFRESH_TOKEN);
      } catch {
        refreshToken = null;
      }
      if (!(error instanceof HttpErrorResponse) || error.status !== 401 || esAuth || !refreshToken) {
        return throwError(() => error);
      }

      refreshRequest ??= auth.renovarSesion().pipe(
        shareReplay({ bufferSize: 1, refCount: false }),
        finalize(() => (refreshRequest = null)),
      );
      return refreshRequest.pipe(
        switchMap(() => {
          const tokenRenovado = auth.obtenerToken();
          if (!tokenRenovado) return throwError(() => error);
          return siguiente(peticion.clone({ setHeaders: { Authorization: `Bearer ${tokenRenovado}` } }));
        }),
        catchError((errorRenovacion: unknown) => {
          auth.limpiarSesion();
          return throwError(() => errorRenovacion);
        }),
      );
    }),
  );
};
