import { Component, signal } from '@angular/core';
import { Sidebar } from '../../components/sidebar/sidebar';
import { EduTrackDataService, FilaImportacionEstudiante } from '../../services/edutrack-data.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-importar-estudiantes', imports: [Sidebar],
  templateUrl: './importar-estudiantes.html',
})
export class ImportarEstudiantes {
  readonly filas = signal<FilaImportacionEstudiante[]>([]);
  readonly cargando = signal(false);
  readonly confirmando = signal(false);
  readonly revisada = signal(false);
  readonly error = signal<string | null>(null);
  readonly resultado = signal<{ importados: number; omitidos: number; detalleOmitidos: { fila: number; matricula: string; motivo: string }[] } | null>(null);
  readonly nombreArchivo = signal('');
  get validas(): number { return this.filas().filter((fila) => fila.valida).length; }
  get conErrores(): number { return this.filas().length - this.validas; }

  constructor(private readonly api: EduTrackDataService) {}

  seleccionar(evento: Event): void {
    const archivo = (evento.target as HTMLInputElement).files?.[0];
    this.error.set(null); this.resultado.set(null); this.revisada.set(false); this.filas.set([]);
    if (!archivo) return;
    if (!/\.(csv|xlsx)$/i.test(archivo.name)) { this.error.set('Selecciona un archivo CSV o XLSX.'); return; }
    this.nombreArchivo.set(archivo.name); this.cargando.set(true);
    this.api.validarImportacionEstudiantes(archivo).subscribe({
      next: (r) => { this.filas.set(r.filas); this.cargando.set(false); },
      error: (e) => { this.error.set(mensajeDeError(e)); this.cargando.set(false); },
    });
  }

  confirmar(): void {
    if (!this.revisada() || !this.filas().length || this.confirmando()) return;
    this.confirmando.set(true); this.error.set(null);
    this.api.confirmarImportacionEstudiantes(this.filas()).subscribe({
      next: (r) => { this.resultado.set(r); this.confirmando.set(false); this.revisada.set(false); },
      error: (e) => { this.error.set(mensajeDeError(e)); this.confirmando.set(false); },
    });
  }
}
