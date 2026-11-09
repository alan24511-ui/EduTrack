import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-recuperar-password',
  imports: [FormsModule, RouterLink],
  templateUrl: './recuperar-password.html',
})
export class RecuperarPassword {
  correo = '';
  token = '';
  nuevaPassword = '';
  solicitado = false;
  readonly error = signal<string | null>(null);
  readonly aviso = signal<string | null>(null);
  readonly cargando = signal(false);

  constructor(private readonly auth: AuthService) {}

  solicitar(): void {
    this.ejecutar(this.auth.solicitarRecuperacion(this.correo), (r) => {
      this.solicitado = true;
      this.aviso.set(r.mensaje);
    });
  }

  reenviar(): void {
    this.ejecutar(this.auth.reenviarOtp(this.correo, 'recovery'), (r) => this.aviso.set(r.mensaje));
  }

  guardarPassword(): void {
    this.ejecutar(
      this.auth.restablecerPassword(this.correo, this.token.trim(), this.nuevaPassword),
      (r) => this.aviso.set(r.mensaje),
    );
  }

  private ejecutar<T extends { mensaje: string }>(solicitud: import('rxjs').Observable<T>, ok: (r: T) => void): void {
    this.error.set(null);
    this.aviso.set(null);
    this.cargando.set(true);
    solicitud.subscribe({
      next: (r) => { this.cargando.set(false); ok(r); },
      error: (e) => { this.cargando.set(false); this.error.set(mensajeDeError(e)); },
    });
  }
}
