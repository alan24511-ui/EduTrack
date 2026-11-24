import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

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
  q = '';
  grupo = '';
  parentesco = 'Madre';

  readonly parentescos = ['Madre', 'Padre', 'Tutor legal', 'Abuelo(a)', 'Hermano(a)', 'Otro'];
  readonly cargando = signal(false);
  readonly buscando = signal(false);
  readonly error = signal<string | null>(null);
  readonly estudiantes = signal<EstudianteVinculacion[]>([]);
  readonly grupos = signal<string[]>([]);
  readonly estudianteSeleccionado = signal<EstudianteVinculacion | null>(null);
  readonly completado = signal(false);

  constructor(readonly auth: AuthService, private readonly vinculacion: VinculacionService) {}

  buscar(): void {
    this.error.set(null);
    this.estudianteSeleccionado.set(null);
    if (this.q.trim().length < 2 && !this.grupo) {
      this.estudiantes.set([]);
      this.error.set('Escribe al menos 2 caracteres o selecciona un grupo.');
      return;
    }
    this.buscando.set(true);
    this.vinculacion.buscar(this.q.trim(), this.grupo).subscribe({
      next: (respuesta) => {
        this.grupos.set(respuesta.grupos);
        this.estudiantes.set(respuesta.estudiantes);
        this.buscando.set(false);
      },
      error: (error: unknown) => {
        this.buscando.set(false);
        this.error.set(mensajeDeError(error));
      },
    });
  }

  seleccionar(estudiante: EstudianteVinculacion): void {
    this.error.set(null);
    this.estudianteSeleccionado.set(estudiante);
  }

  confirmar(): void {
    const estudiante = this.estudianteSeleccionado();
    if (!estudiante) return;
    this.error.set(null);
    this.cargando.set(true);
    this.vinculacion.confirmar(estudiante.id, this.parentesco).subscribe({
      next: () => {
        this.cargando.set(false);
        this.completado.set(true);
        this.estudianteSeleccionado.set(null);
      },
      error: (error: unknown) => {
        this.cargando.set(false);
        this.error.set(mensajeDeError(error));
      },
    });
  }
}
