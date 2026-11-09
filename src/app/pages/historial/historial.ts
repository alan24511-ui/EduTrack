import { Component, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Layout } from '../../components/layout/layout';
import { AsistenciaRegistro, EduTrackDataService } from '../../services/edutrack-data.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  imports: [Layout, FormsModule, DatePipe],
  selector: 'app-historial',
  templateUrl: './historial.html',
})
export class Historial implements OnInit {
  readonly filas = signal<AsistenciaRegistro[]>([]);
  readonly error = signal<string | null>(null);
  readonly cargando = signal(false);
  readonly grupos = signal<string[]>([]);
  readonly estados = signal<string[]>([]);
  desde = '';
  hasta = '';
  q = '';
  grupo = '';
  estado = '';
  constructor(private readonly api: EduTrackDataService) {}
  ngOnInit(): void {
    this.api.estudiantes().subscribe({
      next: (rows) => this.grupos.set([...new Set(rows.map((r) => r.grupo))].sort()),
      error: (e) => this.error.set(mensajeDeError(e)),
    });
    this.buscar();
  }

  get visibles(): AsistenciaRegistro[] {
    return this.filas().filter((row) => !this.estado || row.estado === this.estado);
  }

  buscar(): void {
    this.error.set(null); this.cargando.set(true);
    this.api.historial({ desde: this.desde, hasta: this.hasta, q: this.q, grupo: this.grupo }).subscribe({
      next: (rows) => {
        this.filas.set(rows);
        this.estados.set([...new Set(rows.map((r) => r.estado))].sort());
        this.cargando.set(false);
      },
      error: (e) => { this.error.set(mensajeDeError(e)); this.cargando.set(false); },
    });
  }

  exportar(): void {
    const encabezados = ['Fecha', 'Matrícula', 'Estudiante', 'Grupo', 'Hora entrada', 'Hora salida', 'Estado'];
    const filas = this.visibles.map((r) => [r.fecha, r.matricula, r.nombre, r.grupo, r.horaEntrada ?? '', r.horaSalida ?? '', r.estado]);
    const contenido = [encabezados, ...filas]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(','))
      .join('\r\n');
    const archivo = new Blob([`\uFEFF${contenido}`], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(archivo);
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = 'historial-asistencias.csv';
    enlace.click();
    URL.revokeObjectURL(url);
  }
}
