import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Layout } from '../../components/layout/layout';
import { EduTrackDataService, Estudiante, Tarjeta } from '../../services/edutrack-data.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  imports: [Layout, FormsModule],
  selector: 'app-tarjetas',
  styleUrl: './tarjetas.css',
  templateUrl: './tarjetas.html',
})
export class Tarjetas implements OnInit {
  readonly tarjetas = signal<Tarjeta[]>([]);
  readonly estudiantes = signal<Estudiante[]>([]);
  readonly error = signal<string | null>(null);
  readonly aviso = signal<string | null>(null);
  readonly cargando = signal(false);
  readonly editando = signal<number | null>(null);
  readonly formularioVisible = signal(false);
  readonly lector = signal<{ nombre: string; conectado: boolean } | null>(null);
  buscar = '';
  uid = '';
  idEstudiante = '';
  propietario = '';
  vigenciaInicio = '';
  vigenciaTermino = '';

  constructor(private readonly api: EduTrackDataService) {}
  ngOnInit(): void {
    this.cargar();
    this.api.estudiantes().subscribe({ next: (v) => this.estudiantes.set(v), error: (e) => this.error.set(mensajeDeError(e)) });
    this.api.dashboard().subscribe({
      next: (data) => this.lector.set(data.lectores?.[0] ?? null),
      error: (e) => this.error.set(mensajeDeError(e)),
    });
  }
  cargar(): void {
    this.cargando.set(true);
    this.api.tarjetas().subscribe({ next: (v) => { this.tarjetas.set(v); this.cargando.set(false); }, error: (e) => { this.error.set(mensajeDeError(e)); this.cargando.set(false); } });
  }
  get visibles(): Tarjeta[] {
    const q = this.buscar.trim().toUpperCase();
    return this.tarjetas().filter((t) => !q || `${t.uid} ${t.nombreEstudiante} ${t.matricula}`.toUpperCase().includes(q));
  }
  guardar(): void {
    this.error.set(null); this.aviso.set(null); this.cargando.set(true);
    const data = { uid: this.uid.trim().toUpperCase(), id_estudiante: Number(this.idEstudiante), propietario: this.propietario.trim() || null, vigencia_inicio: this.vigenciaInicio || null, vigencia_termino: this.vigenciaTermino || null };
    const solicitud = this.editando() === null ? this.api.crearTarjeta(data) : this.api.reemplazarTarjeta(this.editando()!, data);
    solicitud.subscribe({ next: () => { this.aviso.set('Tarjeta guardada.'); this.limpiar(); this.cargar(); }, error: (e) => { this.error.set(mensajeDeError(e)); this.cargando.set(false); } });
  }
  iniciarAsociacion(): void { this.limpiar(); this.formularioVisible.set(true); }
  editar(t: Tarjeta): void {
    this.formularioVisible.set(true);
    this.editando.set(t.idTarjeta); this.uid = t.uid; this.idEstudiante = String(t.idEstudiante);
    this.propietario = t.propietario ?? ''; this.vigenciaInicio = t.vigenciaInicio ?? ''; this.vigenciaTermino = t.vigenciaTermino ?? '';
  }
  cancelar(): void { this.limpiar(); }
  async copiarUid(): Promise<void> {
    if (!this.uid.trim()) return;
    try { await navigator.clipboard.writeText(this.uid.trim().toUpperCase()); this.aviso.set('UID copiado.'); }
    catch { this.error.set('No se pudo copiar el UID desde este navegador.'); }
  }
  nombreEstudianteSeleccionado(): string {
    return this.estudiantes().find((s) => String(s.id) === this.idEstudiante)?.nombre ?? 'Sin estudiante seleccionado';
  }
  estadoTarjetaSeleccionada(): string {
    const tarjeta = this.tarjetas().find((t) => t.idTarjeta === this.editando());
    return tarjeta ? (tarjeta.vigente ? 'Vigente' : 'Fuera de vigencia') : 'Pendiente de registrar';
  }
  limpiar(): void { this.editando.set(null); this.uid = ''; this.idEstudiante = ''; this.propietario = ''; this.vigenciaInicio = ''; this.vigenciaTermino = ''; this.cargando.set(false); this.formularioVisible.set(false); }
}
