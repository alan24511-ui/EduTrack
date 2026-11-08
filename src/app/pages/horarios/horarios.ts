import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Sidebar } from '../../components/sidebar/sidebar';
import { AuthService } from '../../services/auth.service';
import { EduTrackDataService, HorarioPublicado } from '../../services/edutrack-data.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-horarios',
  imports: [FormsModule, Sidebar],
  templateUrl: './horarios.html',
})
export class Horarios implements OnInit {
  readonly horarios = signal<HorarioPublicado[]>([]);
  readonly error = signal<string | null>(null);
  readonly mensaje = signal<string | null>(null);
  readonly filtroGrupo = signal('');
  readonly editando = signal<number | null>(null);
  readonly admin = () => ['administrador', 'superadministrador'].includes(this.auth.rol() ?? '');
  readonly formulario = signal({ diaSemana: '', grupo: '', horaEntrada: '', horaSalida: '', tolerancia: 0 });

  constructor(readonly auth: AuthService, private readonly api: EduTrackDataService) {}
  ngOnInit(): void { this.cargar(); }
  get visibles(): HorarioPublicado[] {
    const filtro = this.filtroGrupo().trim().toLocaleLowerCase();
    return this.horarios().filter((h) => !filtro || h.grupo.toLocaleLowerCase().includes(filtro));
  }
  cargar(): void {
    this.api.horarios().subscribe({ next: (rows) => this.horarios.set(rows), error: (e: unknown) => this.error.set(mensajeDeError(e)) });
  }
  set(campo: keyof ReturnType<typeof this.formulario>, value: string | number): void {
    this.formulario.update((form) => ({ ...form, [campo]: value }));
  }
  editar(h: HorarioPublicado): void {
    this.editando.set(h.id);
    this.formulario.set({ diaSemana: h.diaSemana, grupo: h.grupo, horaEntrada: h.horaEntrada, horaSalida: h.horaSalida, tolerancia: h.tolerancia });
  }
  cancelarEdicion(): void {
    this.editando.set(null);
    this.formulario.set({ diaSemana: '', grupo: '', horaEntrada: '', horaSalida: '', tolerancia: 0 });
  }
  guardar(): void {
    const data = this.formulario(); this.error.set(null); this.mensaje.set(null);
    const id = this.editando();
    const request = id === null ? this.api.crearHorario(data) : this.api.actualizarHorario(id, data);
    request.subscribe({
      next: () => { this.mensaje.set('Horario guardado y publicado. Los tutores ya pueden consultar esta versión.'); this.cancelarEdicion(); this.cargar(); },
      error: (e: unknown) => this.error.set(mensajeDeError(e)),
    });
  }
  eliminar(h: HorarioPublicado): void {
    if (!window.confirm(`¿Eliminar el horario del grupo ${h.grupo} para ${h.diaSemana}?`)) return;
    this.api.eliminarHorario(h.id).subscribe({
      next: () => { this.mensaje.set('Horario eliminado.'); this.cargar(); },
      error: (e: unknown) => this.error.set(mensajeDeError(e)),
    });
  }
}
