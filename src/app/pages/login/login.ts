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
  styleUrl: './login.css'
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
        this.router.navigate([respuesta.requiere_vinculacion ? '/vinculacion' : '/admin']);
      },
      error: (error) => {
        this.cargando.set(false);
        this.error.set(mensajeDeError(error));
      },
    });
  }
}
