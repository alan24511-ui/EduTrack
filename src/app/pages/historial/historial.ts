import { Component, OnDestroy, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Layout } from '../../components/layout/layout';
import { AsistenciaRegistro, EduTrackDataService, EventoLector } from '../../services/edutrack-data.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  imports: [Layout, FormsModule, DatePipe],
  selector: 'app-historial',
  templateUrl: './historial.html',
})
export class Historial implements OnInit, OnDestroy {
  readonly filas = signal<AsistenciaRegistro[]>([]);
  readonly error = signal<string | null>(null);
  readonly cargando = signal(false);
  readonly grupos = signal<string[]>([]);
  readonly estados = signal<string[]>([]);
  readonly eventosLector = signal<EventoLector[]>([]);
  desde = '';
  hasta = '';
  q = '';
  grupo = '';
  estado = '';
  private ultimoEventoLector = 0;
  private eventosTimer: ReturnType<typeof setInterval> | null = null;
  private eventosPollingDisponible = true;
  constructor(private readonly api: EduTrackDataService) {}
  ngOnInit(): void {
    this.api.estudiantes().subscribe({
      next: (rows) => this.grupos.set([...new Set(rows.map((r) => r.grupo))].sort()),
      error: (e) => this.error.set(mensajeDeError(e)),
    });
    this.buscar();
    this.consultarEventosLector();
    this.eventosTimer = setInterval(() => this.consultarEventosLector(), 3000);
  }
  ngOnDestroy(): void { if (this.eventosTimer) clearInterval(this.eventosTimer); }

  private consultarEventosLector(): void {
    if (!this.eventosPollingDisponible) return;
    this.api.eventosLector(this.ultimoEventoLector).subscribe({
      next: (response) => {
        this.ultimoEventoLector = response.lastId;
        if (!response.eventos.length) return;
        this.eventosLector.update((actuales) => [...response.eventos, ...actuales].slice(0, 5));
        if (response.eventos.some((e) => e.resultado === 'ENTRADA_REGISTRADA' || e.resultado === 'SALIDA_REGISTRADA')) this.buscar();
      },
      error: () => { this.eventosPollingDisponible = false; },
    });
  }

  claseEvento(resultado: EventoLector['resultado']): string {
    if (resultado === 'ENTRADA_REGISTRADA') return 'alert-success';
    if (resultado === 'SALIDA_REGISTRADA') return 'alert-primary';
    if (resultado === 'LECTURA_DUPLICADA') return 'alert-secondary';
    if (resultado === 'ASISTENCIA_COMPLETA') return 'alert-info';
    return 'alert-danger';
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
