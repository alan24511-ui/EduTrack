import { Component, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../services/auth.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './login.html',
})
export class Login {
  correo = '';
  password = '';

  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);

  constructor(
    private readonly router: Router,
    private readonly auth: AuthService,
  ) {}

  iniciarSesion() {
    this.error.set(null);
    this.cargando.set(true);

    this.auth.iniciarSesion(this.correo, this.password).subscribe({
      next: (respuesta) => {
        this.cargando.set(false);
        const destino = respuesta.rol === 'administrador' || respuesta.rol === 'superadministrador'
          ? '/admin'
          : respuesta.requiere_vinculacion ? '/vinculacion' : '/dashboard-papas';
        void this.router.navigate([destino]);
      },
      error: (error) => {
        this.cargando.set(false);
        this.error.set(mensajeDeError(error));
      },
    });
  }
}
