import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../services/auth.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-registro',
  imports: [FormsModule, RouterLink],
  templateUrl: './registro.html',
})
export class Registro {
  nombre = '';
  correo = '';
  password = '';

  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);

  constructor(
    private readonly auth: AuthService,
    private readonly router: Router,
  ) {}

  registrar(): void {
    this.error.set(null);
    this.cargando.set(true);

    this.auth.registrar(this.nombre, this.correo, this.password).subscribe({
      next: () => {
        this.cargando.set(false);
        this.router.navigate(['/verificar-otp'], {
          queryParams: { correo: this.correo },
        });
      },
      error: (error) => {
        this.cargando.set(false);
        this.error.set(mensajeDeError(error));
      },
    });
  }
}
