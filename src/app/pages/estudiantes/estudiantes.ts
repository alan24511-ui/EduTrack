import { Component, OnDestroy, OnInit, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Sidebar } from '../../components/sidebar/sidebar';
import { EduTrackDataService, Estudiante } from '../../services/edutrack-data.service';
import { mensajeDeError } from '../../utils/errores';
import { Subscription } from 'rxjs';

@Component({
  imports: [Sidebar, FormsModule],
  selector: 'app-estudiantes',
  templateUrl: './estudiantes.html',
})
export class Estudiantes implements OnInit, OnDestroy {
  readonly lista = signal<Estudiante[]>([]);
  readonly error = signal<string | null>(null);
  readonly aviso = signal<string | null>(null);
  readonly cargando = signal(false);
  readonly editando = signal<number | null>(null);
  readonly formularioVisible = signal(false);
  readonly tutoresAbiertos = signal<number | null>(null);
  readonly grupos = computed(() => [...new Set(this.lista().map((s) => s.grupo))].sort());
  readonly lector = signal<{ conectado: boolean; puerto: string | null; lectorListo: boolean; capturando: boolean; error: string | null } | null>(null);
  readonly alumnoRFID = signal<Estudiante | null>(null);
  readonly estadoRFID = signal<'comprobando' | 'leyendo' | 'exito' | 'error' | 'cancelado'>('comprobando');
  readonly resultadoRFID = signal<string | null>(null);
  readonly alumnoNuevo = signal<Estudiante | null>(null);
  buscar = '';
  grupoFiltro = '';
  nombre = '';
  matricula = '';
  grupo = '';
  correo = '';
  private solicitudLectura: Subscription | null = null;
  private capturaId: string | null = null;
  private estadoTimer: ReturnType<typeof setInterval> | null = null;

  constructor(private readonly api: EduTrackDataService) {}
  ngOnInit(): void { this.cargar(); this.consultarLector(); this.estadoTimer = setInterval(() => this.consultarLector(), 5000); }
  ngOnDestroy(): void {
    if (this.estadoRFID() === 'leyendo' && this.capturaId) this.api.cancelarLecturaRFID(this.capturaId).subscribe({ error: () => undefined });
    this.solicitudLectura?.unsubscribe(); if (this.estadoTimer) clearInterval(this.estadoTimer);
  }

  nuevo(): void { this.limpiar(); this.formularioVisible.set(true); }

  cargar(): void {
    this.cargando.set(true);
    this.api.estudiantes().subscribe({
      next: (data) => { this.lista.set(data); this.cargando.set(false); },
      error: (e) => { this.error.set(mensajeDeError(e)); this.cargando.set(false); },
    });
  }

  consultarLector(): void {
    this.api.estadoLector().subscribe({ next: (estado) => this.lector.set(estado), error: (e) => this.lector.set({ conectado: false, lectorListo: false, puerto: null, capturando: false, error: mensajeDeError(e) }) });
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
      next: (alumno) => {
        const esNuevo = this.editando() === null;
        this.aviso.set(esNuevo ? 'Estudiante registrado.' : 'Cambios guardados.');
        this.limpiar(); this.cargar();
        if (esNuevo) this.alumnoNuevo.set(alumno);
      },
      error: (e) => { this.error.set(mensajeDeError(e)); this.cargando.set(false); },
    });
  }

  editar(s: Estudiante): void {
    this.formularioVisible.set(true);
    this.editando.set(s.id); this.nombre = s.nombre; this.matricula = s.matricula;
    this.grupo = s.grupo; this.correo = s.correoInstitucional ?? '';
  }

  cancelar(): void { this.limpiar(); }
  asociarAhora(alumno: Estudiante): void { this.alumnoNuevo.set(null); this.abrirAsociacion(alumno); }
  posponerAsociacion(): void { this.alumnoNuevo.set(null); }
  abrirAsociacion(alumno: Estudiante): void {
    if (this.estadoRFID() === 'leyendo' && this.capturaId) this.api.cancelarLecturaRFID(this.capturaId).subscribe({ error: () => undefined });
    this.solicitudLectura?.unsubscribe();
    this.alumnoRFID.set(alumno); this.resultadoRFID.set(null); this.estadoRFID.set('comprobando');
    this.consultarLector(); this.iniciarLectura();
  }
  iniciarLectura(): void {
    const alumno = this.alumnoRFID();
    if (!alumno) return;
    this.estadoRFID.set('comprobando'); this.resultadoRFID.set(null);
    this.api.estadoLector().subscribe({
      next: (estado) => {
        this.lector.set(estado);
        if (!estado.conectado || !estado.lectorListo) { this.estadoRFID.set('error'); this.resultadoRFID.set(estado.error || 'Lector desconectado. Comprueba el cable USB y reintenta.'); return; }
        this.estadoRFID.set('leyendo');
        const captureId = crypto.randomUUID();
        this.capturaId = captureId;
        this.solicitudLectura = this.api.asociarTarjetaLeida(alumno.id, captureId).subscribe({
          next: (r) => { if (this.alumnoRFID()?.id !== alumno.id || this.capturaId !== captureId) return; this.capturaId = null; this.estadoRFID.set('exito'); this.resultadoRFID.set(`Tarjeta ${r.uid} asociada correctamente.`); this.consultarLector(); this.cargar(); },
          error: (e) => { if (this.alumnoRFID()?.id !== alumno.id || this.capturaId !== captureId) return; this.capturaId = null; this.estadoRFID.set('error'); this.resultadoRFID.set(mensajeDeError(e)); this.consultarLector(); },
        });
      },
      error: (e) => { this.lector.set({ conectado: false, lectorListo: false, puerto: null, capturando: false, error: mensajeDeError(e) }); this.estadoRFID.set('error'); this.resultadoRFID.set('No fue posible consultar el estado del lector.'); },
    });
  }
  cerrarAsociacion(): void {
    if (this.estadoRFID() === 'leyendo' && this.capturaId) this.api.cancelarLecturaRFID(this.capturaId).subscribe({ error: () => undefined });
    this.capturaId = null;
    this.solicitudLectura?.unsubscribe(); this.solicitudLectura = null;
    this.alumnoRFID.set(null); this.consultarLector();
  }
  alternarTutores(id: number): void { this.tutoresAbiertos.set(this.tutoresAbiertos() === id ? null : id); }
  private limpiar(): void {
    this.editando.set(null); this.nombre = ''; this.matricula = ''; this.grupo = ''; this.correo = '';
    this.cargando.set(false); this.formularioVisible.set(false);
  }
}
