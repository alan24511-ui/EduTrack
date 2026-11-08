import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, provideRouter, Router, RouterStateSnapshot, UrlTree } from '@angular/router';
import { firstValueFrom, Observable, of, throwError } from 'rxjs';

import { routes } from '../app.routes';
import { AuthService, PerfilUsuario } from '../services/auth.service';
import { adminGuard, authGuard, tutorGuard } from './role.guards';

describe('role guards', () => {
  let perfil: PerfilUsuario;
  let auth: { cargarPerfil: ReturnType<typeof vi.fn>; limpiarSesion: ReturnType<typeof vi.fn> };
  let router: Router;

  beforeEach(() => {
    perfil = { tutor: null, rol: 'tutor' };
    auth = {
      cargarPerfil: vi.fn(() => of(perfil)),
      limpiarSesion: vi.fn(),
    };
    TestBed.configureTestingModule({
      providers: [provideRouter(routes), { provide: AuthService, useValue: auth }],
    });
    router = TestBed.inject(Router);
  });

  function ejecutar(guard: typeof adminGuard | typeof authGuard | typeof tutorGuard) {
    return TestBed.runInInjectionContext(() =>
      firstValueFrom(
        guard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot) as Observable<boolean | UrlTree>,
      ),
    );
  }

  it('denies a tutor access to administrative routes and sends them to linking', async () => {
    const resultado = await ejecutar(adminGuard);
    expect(resultado instanceof UrlTree).toBe(true);
    expect(router.serializeUrl(resultado as UrlTree)).toBe('/vinculacion');
  });

  it('allows an administrator into administrative routes', async () => {
    perfil = { tutor: null, rol: 'administrador' };
    expect(await ejecutar(adminGuard)).toBe(true);
  });

  it('allows only a tutor into parent modules', async () => {
    expect(await ejecutar(tutorGuard)).toBe(true);
    perfil = { tutor: null, rol: 'administrador' };
    const resultado = await ejecutar(tutorGuard);
    expect(resultado instanceof UrlTree).toBe(true);
    expect(router.serializeUrl(resultado as UrlTree)).toBe('/admin');
  });

  it('allows a signed-in tutor into linking after checking the backend profile', async () => {
    expect(await ejecutar(authGuard)).toBe(true);
    expect(auth.cargarPerfil).toHaveBeenCalledOnce();
  });

  it('sends an unauthenticated user to login and clears an invalid session', async () => {
    auth.cargarPerfil.mockReturnValueOnce(
      throwError(() => new HttpErrorResponse({ status: 401 })),
    );
    const resultado = await ejecutar(authGuard);
    expect(resultado instanceof UrlTree).toBe(true);
    expect(router.serializeUrl(resultado as UrlTree)).toBe('/login');
    expect(auth.limpiarSesion).toHaveBeenCalledOnce();
  });

  it('protects administrative routes with admin guard and scoped views with auth guard', () => {
    for (const path of ['admin', 'estudiantes', 'tarjetas', 'configuracion']) {
      expect(routes.find((route) => route.path === path)?.canActivate).toContain(adminGuard);
    }
    for (const path of ['dashboard', 'historial', 'horarios']) {
      expect(routes.find((route) => route.path === path)?.canActivate).toContain(authGuard);
    }
    for (const path of ['dashboard-papas', 'configuracion-papas']) {
      expect(routes.find((route) => route.path === path)?.canActivate).toContain(tutorGuard);
    }
  });
});
