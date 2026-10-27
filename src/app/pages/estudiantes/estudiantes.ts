
import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import {
  Api,
  Estudiante,
  NuevoEstudiante,
} from '../../services/api';

@Component({
  selector: 'app-estudiantes',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  styleUrl: './estudiantes.css',
  templateUrl: './estudiantes.html',
})
export class Estudiantes implements OnInit {
  private readonly api = inject(Api);

  estudiantes: Estudiante[] = [];
  busqueda = '';

  cargando = false;
  guardando = false;
  mostrarFormulario = false;

  error = '';
  mensaje = '';

  nuevo: NuevoEstudiante = this.formularioVacio();

  ngOnInit(): void {
    this.cargarEstudiantes();
  }

  // Filtra los estudiantes por matrícula, nombre, grupo o correo.
  get estudiantesFiltrados(): Estudiante[] {
    const texto = this.busqueda.trim().toLowerCase();

    if (!texto) {
      return this.estudiantes;
    }

    return this.estudiantes.filter((estudiante) =>
      [
        estudiante.Matricula,
        estudiante.Nombre,
        estudiante.Grupo,
        estudiante.Correo_Institucional ?? '',
      ].some((valor) =>
        String(valor ?? '').toLowerCase().includes(texto),
      ),
    );
  }

  // Total de estudiantes cargados en la tabla.
  get totalEstudiantes(): number {
    return this.estudiantes.length;
  }

  private formularioVacio(): NuevoEstudiante {
    return {
      Matricula: '',
      Nombre: '',
      Grupo: '',
      Correo_Institucional: '',
    };
  }

  // Consulta los estudiantes desde FastAPI y Supabase.
  cargarEstudiantes(): void {
    this.cargando = true;
    this.error = '';

    console.log('Consultando estudiantes en la API...');

    this.api.obtenerEstudiantes().subscribe({
      next: (datos) => {
        console.log('Respuesta de la API:', datos);
        console.log('¿Es una lista?', Array.isArray(datos));
        console.log('Cantidad recibida:', datos?.length);

        if (!Array.isArray(datos)) {
          this.estudiantes = [];
          this.error =
            'La API respondió, pero los datos no tienen el formato esperado.';
          this.cargando = false;
          return;
        }

        this.estudiantes = datos;
        this.cargando = false;

        console.log(
          'Cargando después de recibir datos:',
          this.cargando,
        );
      },

      error: (err) => {
        console.error('Error al cargar estudiantes:', err);

        this.error =
          err.error?.detail ??
          'No se pudieron cargar los estudiantes. Verifica que la API esté activa.';

        this.cargando = false;
      },
    });
  }

  // Abre el formulario para registrar un alumno.
  abrirFormulario(): void {
    this.nuevo = this.formularioVacio();
    this.error = '';
    this.mensaje = '';
    this.mostrarFormulario = true;
  }

  // Cierra el formulario.
  cerrarFormulario(): void {
    if (!this.guardando) {
      this.mostrarFormulario = false;
      this.error = '';
    }
  }

  // Registra un estudiante en la base de datos.
  guardarEstudiante(): void {
    this.error = '';
    this.mensaje = '';

    const estudiante: NuevoEstudiante = {
      Matricula: this.nuevo.Matricula.trim(),
      Nombre: this.nuevo.Nombre.trim(),
      Grupo: this.nuevo.Grupo.trim(),
      Correo_Institucional:
        this.nuevo.Correo_Institucional?.trim() || null,
    };

    if (
      !estudiante.Matricula ||
      !estudiante.Nombre ||
      !estudiante.Grupo
    ) {
      this.error =
        'Completa la matrícula, el nombre y el grupo.';
      return;
    }

    this.guardando = true;

    this.api.crearEstudiante(estudiante).subscribe({
      next: () => {
        this.guardando = false;
        this.mostrarFormulario = false;
        this.nuevo = this.formularioVacio();
        this.mensaje =
          'Estudiante registrado correctamente.';

        this.cargarEstudiantes();
      },

      
error: (err) => {
  console.error('ERROR COMPLETO AL REGISTRAR:', err);
  console.error('Código HTTP:', err.status);
  console.error('Respuesta del servidor:', err.error);

  const detalle = err.error?.detail;

  this.error =
    typeof detalle === 'string'
      ? detalle
      : detalle
        ? JSON.stringify(detalle)
        : `No fue posible registrar al estudiante. Error HTTP: ${err.status}`;

  this.guardando = false;
},

    });
  }

  // Elimina un estudiante después de pedir confirmación.
  eliminarEstudiante(estudiante: Estudiante): void {
    const confirmar = window.confirm(
      `¿Seguro que deseas eliminar a ${estudiante.Nombre} (${estudiante.Matricula})? Esta acción no se puede deshacer.`,
    );

    if (!confirmar) {
      return;
    }

    this.error = '';
    this.mensaje = '';

    this.api
      .eliminarEstudiante(estudiante.Id_Estudiante)
      .subscribe({
        next: () => {
          this.mensaje =
            'Estudiante eliminado correctamente.';

          this.cargarEstudiantes();
        },

        error: (err) => {
          console.error(
            'Error al eliminar estudiante:',
            err,
          );

          this.error =
            err.error?.detail ??
            'No fue posible eliminar al estudiante.';
        },
      });
  }
}
