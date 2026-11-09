import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { AuthService, RespuestaLogin } from '../../services/auth.service';
import { Login } from './login';

describe('Login', () => {
  let component: Login;
  let fixture: ComponentFixture<Login>;
  let auth: AuthService;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Login],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()]
    })
      .compileComponents();

    fixture = TestBed.createComponent(Login);
    component = fixture.componentInstance;
    auth = TestBed.inject(AuthService);
    router = TestBed.inject(Router);
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it.each([
    [{ rol: 'tutor', requiere_vinculacion: true }, '/vinculacion'],
    [{ rol: 'tutor', requiere_vinculacion: false }, '/dashboard-papas'],
    [{ rol: 'administrador', requiere_vinculacion: false }, '/admin'],
    [{ rol: 'superadministrador', requiere_vinculacion: false }, '/admin'],
  ] as const)('redirects after login according to the backend role/link state', (data, destino) => {
    const respuesta: RespuestaLogin = {
      sesion: { access_token: 'token', refresh_token: null, expires_in: 60, token_type: 'bearer' },
      tutor: null,
      requiere_vinculacion: data.requiere_vinculacion,
      rol: data.rol,
    };
    vi.spyOn(auth, 'iniciarSesion').mockReturnValue(of(respuesta));
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    component.iniciarSesion();
    expect(navegar).toHaveBeenCalledWith([destino]);
  });
});
