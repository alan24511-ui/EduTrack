import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

import { environment } from '../../environments/environment';

export interface Tutor {
  idTutor: number;
  nombre: string;
  telefono: string | null;
  correo: string;
}

export interface Sesion {
  access_token: string;
  refresh_token: string | null;
  expires_in: number | null;
  token_type: string;
}

export interface RespuestaRegistro {
  mensaje: string;
  requiere_verificacion: boolean;
  correo: string;
}

export interface RespuestaOtp {
  mensaje: string;
  sesion: Sesion;
  tutor: Tutor;
}

export interface RespuestaLogin {
  sesion: Sesion;
  tutor: Tutor | null;
  requiere_vinculacion: boolean;
}

export const CLAVE_ACCESS_TOKEN = 'edutrack.access_token';
export const CLAVE_REFRESH_TOKEN = 'edutrack.refresh_token';
export const CLAVE_TUTOR = 'edutrack.tutor';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly apiUrl = `${environment.apiUrl}/auth`;

  /** Tutor autenticado (null si no hay sesión). */
  readonly tutor = signal<Tutor | null>(this.leerTutorGuardado());

  constructor(private readonly http: HttpClient) {}

  registrar(nombre: string, correo: string, password: string): Observable<RespuestaRegistro> {
    return this.http.post<RespuestaRegistro>(`${this.apiUrl}/register-tutor`, {
      nombre,
      correo,
      password,
    });
  }

  verificarOtp(correo: string, token: string): Observable<RespuestaOtp> {
    return this.http
      .post<RespuestaOtp>(`${this.apiUrl}/verify-otp`, { correo, token })
      .pipe(
        tap((respuesta) => {
          this.guardarSesion(respuesta.sesion);
          this.guardarTutor(respuesta.tutor);
        }),
      );
  }

  iniciarSesion(correo: string, password: string): Observable<RespuestaLogin> {
    return this.http
      .post<RespuestaLogin>(`${this.apiUrl}/login`, { correo, password })
      .pipe(
        tap((respuesta) => {
          this.guardarSesion(respuesta.sesion);
          this.guardarTutor(respuesta.tutor);
        }),
      );
  }

  cargarPerfil(): Observable<{ tutor: Tutor }> {
    return this.http
      .get<{ tutor: Tutor }>(`${this.apiUrl}/me`)
      .pipe(tap((respuesta) => this.guardarTutor(respuesta.tutor)));
  }

  cerrarSesion(): Observable<{ mensaje: string }> {
    return this.http
      .post<{ mensaje: string }>(`${this.apiUrl}/logout`, {})
      .pipe(tap(() => this.limpiarSesion()));
  }

  limpiarSesion(): void {
    this.borrarClave(CLAVE_ACCESS_TOKEN);
    this.borrarClave(CLAVE_REFRESH_TOKEN);
    this.borrarClave(CLAVE_TUTOR);
    this.tutor.set(null);
  }

  obtenerToken(): string | null {
    return this.leerClave(CLAVE_ACCESS_TOKEN);
  }

  estaAutenticado(): boolean {
    return this.obtenerToken() !== null;
  }

  private guardarSesion(sesion: Sesion): void {
    this.escribirClave(CLAVE_ACCESS_TOKEN, sesion.access_token);
    if (sesion.refresh_token) {
      this.escribirClave(CLAVE_REFRESH_TOKEN, sesion.refresh_token);
    }
  }

  private guardarTutor(tutor: Tutor | null): void {
    if (tutor) {
      this.escribirClave(CLAVE_TUTOR, JSON.stringify(tutor));
    } else {
      this.borrarClave(CLAVE_TUTOR);
    }
    this.tutor.set(tutor);
  }

  private leerTutorGuardado(): Tutor | null {
    const guardado = this.leerClave(CLAVE_TUTOR);
    if (!guardado) {
      return null;
    }
    try {
      return JSON.parse(guardado) as Tutor;
    } catch {
      return null;
    }
  }

  // localStorage no existe en SSR ni en algunos entornos de prueba.
  private leerClave(clave: string): string | null {
    try {
      return localStorage.getItem(clave);
    } catch {
      return null;
    }
  }

  private escribirClave(clave: string, valor: string): void {
    try {
      localStorage.setItem(clave, valor);
    } catch {
      // Entorno sin localStorage: la sesión solo vivirá en memoria.
    }
  }

  private borrarClave(clave: string): void {
    try {
      localStorage.removeItem(clave);
    } catch {
      // Entorno sin localStorage.
    }
  }
}
