import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Sidebar } from '../../components/sidebar/sidebar';
import { AuthService } from '../../services/auth.service';
import { ModulosService } from '../../services/modulos.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-configuracion-papas',
  imports: [FormsModule, Sidebar],
  templateUrl: './configuracion-papas.html',
})
export class ConfiguracionPapas implements OnInit {
  nombre = '';
  telefono = '';
  notificacionesHabilitadas = true;
  nuevaPassword = '';
  readonly error = signal<string | null>(null);
  readonly mensaje = signal<string | null>(null);
  readonly guardando = signal(false);

  constructor(readonly auth: AuthService, private readonly modulos: ModulosService, private readonly router: Router) {}

  ngOnInit(): void {
    this.nombre = this.auth.tutor()?.nombre ?? '';
    this.telefono = this.auth.tutor()?.telefono ?? '';
    this.modulos.preferenciasTutor().subscribe({
      next: (p) => this.notificacionesHabilitadas = p.notificacionesHabilitadas,
      error: (e: unknown) => this.error.set(mensajeDeError(e)),
    });
  }

  guardarPerfil(): void {
    this.error.set(null); this.mensaje.set(null); this.guardando.set(true);
    this.auth.actualizarTutor({ nombre: this.nombre, telefono: this.telefono || null }).subscribe({
      next: () => { this.guardando.set(false); this.mensaje.set('Perfil actualizado.'); },
      error: (e: unknown) => { this.guardando.set(false); this.error.set(mensajeDeError(e)); },
    });
  }

  cambiarNotificaciones(event: Event): void {
    const toggle = event.target as HTMLInputElement;
    const anterior = this.notificacionesHabilitadas;
    this.notificacionesHabilitadas = toggle.checked;
    this.modulos.guardarPreferenciasTutor({ notificacionesHabilitadas: this.notificacionesHabilitadas }).subscribe({
      error: (e: unknown) => { this.notificacionesHabilitadas = anterior; toggle.checked = !anterior; this.error.set(mensajeDeError(e)); },
      next: () => this.mensaje.set('Preferencias guardadas.'),
    });
  }

  guardarPassword(): void {
    this.error.set(null); this.mensaje.set(null);
    this.auth.cambiarPassword(this.nuevaPassword).subscribe({
      next: (r) => { this.nuevaPassword = ''; this.mensaje.set(r.mensaje); },
      error: (e: unknown) => this.error.set(mensajeDeError(e)),
    });
  }

  cerrarSesion(): void {
    this.auth.cerrarSesion().subscribe({
      next: () => void this.router.navigate(['/login']),
      error: () => { this.auth.limpiarSesion(); void this.router.navigate(['/login']); },
    });
  }
}
