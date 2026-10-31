import { inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  return auth.cargarPerfil().pipe(
    map(() => true),
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        auth.limpiarSesion();
      }
      return of(router.createUrlTree(['/login']));
    }),
  );
};

export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  return auth.cargarPerfil().pipe(
    map((perfil) =>
      perfil.rol === 'administrador' ? true : router.createUrlTree(['/vinculacion']),
    ),
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        auth.limpiarSesion();
      }
      return of(router.createUrlTree(['/login']));
    }),
  );
};
