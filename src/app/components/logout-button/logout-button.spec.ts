import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { LogoutButton } from './logout-button';

describe('LogoutButton', () => {
  it('ends the session and navigates to login after logout succeeds', () => {
    const auth = { cerrarSesion: vi.fn(() => of({ mensaje: 'ok' })), limpiarSesion: vi.fn() };
    TestBed.configureTestingModule({ imports: [LogoutButton], providers: [provideRouter([]), { provide: AuthService, useValue: auth }] });
    const router = TestBed.inject(Router);
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const fixture = TestBed.createComponent(LogoutButton);

    fixture.componentInstance.cerrarSesion();
    expect(auth.cerrarSesion).toHaveBeenCalledOnce();
    expect(navigate).toHaveBeenCalledWith(['/login']);
    expect(auth.limpiarSesion).not.toHaveBeenCalled();
  });

  it('clears local credentials and navigates to login if the API cannot log out', () => {
    const auth = { cerrarSesion: vi.fn(() => throwError(() => new Error('offline'))), limpiarSesion: vi.fn() };
    TestBed.configureTestingModule({ imports: [LogoutButton], providers: [provideRouter([]), { provide: AuthService, useValue: auth }] });
    const router = TestBed.inject(Router);
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const fixture = TestBed.createComponent(LogoutButton);

    fixture.componentInstance.cerrarSesion();
    expect(auth.limpiarSesion).toHaveBeenCalledOnce();
    expect(navigate).toHaveBeenCalledWith(['/login']);
  });
});
