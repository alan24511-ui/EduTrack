import { Component, OnInit, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Sidebar } from '../../components/sidebar/sidebar';
import { EduTrackDataService, Estudiante } from '../../services/edutrack-data.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  imports: [Sidebar, FormsModule],
  selector: 'app-estudiantes',
  templateUrl: './estudiantes.html',
})
export class Estudiantes implements OnInit {
  readonly lista = signal<Estudiante[]>([]);
  readonly error = signal<string | null>(null);
  readonly aviso = signal<string | null>(null);
  readonly cargando = signal(false);
  readonly editando = signal<number | null>(null);
  readonly formularioVisible = signal(false);
  readonly tutoresAbiertos = signal<number | null>(null);
  readonly grupos = computed(() => [...new Set(this.lista().map((s) => s.grupo))].sort());
  buscar = '';
  grupoFiltro = '';
  nombre = '';
  matricula = '';
  grupo = '';
  correo = '';

  constructor(private readonly api: EduTrackDataService) {}
  ngOnInit(): void { this.cargar(); }

  nuevo(): void { this.limpiar(); this.formularioVisible.set(true); }

  cargar(): void {
    this.cargando.set(true);
    this.api.estudiantes().subscribe({
      next: (data) => { this.lista.set(data); this.cargando.set(false); },
      error: (e) => { this.error.set(mensajeDeError(e)); this.cargando.set(false); },
    });
  }

  get visibles(): Estudiante[] {
    const q = this.buscar.trim().toLocaleLowerCase();
    return this.lista().filter((s) => (!this.grupoFiltro || s.grupo === this.grupoFiltro)
      && (!q || `${s.nombre} ${s.matricula} ${s.grupo}`.toLocaleLowerCase().includes(q)));
  }

  nombresTutores(s: Estudiante): string {
    return (s.tutores ?? []).map((t) => t.nombre).join(', ') || 'Sin tutor';
  }

  guardar(): void {
    this.error.set(null); this.aviso.set(null); this.cargando.set(true);
    const payload = { nombre: this.nombre.trim(), matricula: this.matricula.trim(), grupo: this.grupo.trim(), correo_institucional: this.correo.trim() || null };
    const solicitud = this.editando() === null
      ? this.api.crearEstudiante(payload)
      : this.api.actualizarEstudiante(this.editando()!, payload);
    solicitud.subscribe({
      next: () => { this.aviso.set(this.editando() === null ? 'Estudiante registrado.' : 'Cambios guardados.'); this.limpiar(); this.cargar(); },
      error: (e) => { this.error.set(mensajeDeError(e)); this.cargando.set(false); },
    });
  }

  editar(s: Estudiante): void {
    this.formularioVisible.set(true);
    this.editando.set(s.id); this.nombre = s.nombre; this.matricula = s.matricula;
    this.grupo = s.grupo; this.correo = s.correoInstitucional ?? '';
  }

  cancelar(): void { this.limpiar(); }
  alternarTutores(id: number): void { this.tutoresAbiertos.set(this.tutoresAbiertos() === id ? null : id); }
  private limpiar(): void {
    this.editando.set(null); this.nombre = ''; this.matricula = ''; this.grupo = ''; this.correo = '';
    this.cargando.set(false); this.formularioVisible.set(false);
  }
}
