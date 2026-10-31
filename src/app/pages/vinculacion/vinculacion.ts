import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { Layout } from '../../components/layout/layout';
import { AuthService } from '../../services/auth.service';
import { EstudianteVinculacion, VinculacionService } from '../../services/vinculacion.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-vinculacion',
  imports: [Layout, FormsModule, RouterLink],
  templateUrl: './vinculacion.html',
})
export class Vinculacion {
  codigo = '';
  parentesco = 'Madre';

  readonly parentescos = ['Madre', 'Padre', 'Tutor legal', 'Abuelo(a)', 'Hermano(a)', 'Otro'];

  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly estudiante = signal<EstudianteVinculacion | null>(null);
  readonly completado = signal(false);

  constructor(
    readonly auth: AuthService,
    private readonly vinculacion: VinculacionService,
    private readonly router: Router,
  ) {
    if (!this.auth.estaAutenticado()) {
      this.router.navigate(['/login']);
    }
  }

  consultar(): void {
    this.error.set(null);
    this.cargando.set(true);

    this.vinculacion.consultar(this.codigo.trim()).subscribe({
      next: (respuesta) => {
        this.cargando.set(false);
        this.estudiante.set(respuesta.estudiante);
      },
      error: (error) => {
        this.cargando.set(false);
        this.estudiante.set(null);
        this.error.set(mensajeDeError(error));
      },
    });
  }

  confirmar(): void {
    this.error.set(null);
    this.cargando.set(true);

    this.vinculacion.confirmar(this.codigo.trim(), this.parentesco).subscribe({
      next: () => {
        this.cargando.set(false);
        this.completado.set(true);
        this.estudiante.set(null);
      },
      error: (error) => {
        this.cargando.set(false);
        this.error.set(mensajeDeError(error));
      },
    });
  }

  reiniciar(): void {
    this.codigo = '';
    this.parentesco = 'Madre';
    this.error.set(null);
    this.estudiante.set(null);
  }
}
