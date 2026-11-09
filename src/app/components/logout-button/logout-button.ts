import { Component, Input, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-logout-button',
  template: `<button type="button" [class]="clases" [disabled]="cargando()" (click)="cerrarSesion()">{{ cargando() ? 'Cerrando sesión…' : 'Cerrar sesión' }}</button>`,
})
export class LogoutButton {
  @Input() clases = 'btn btn-link';
  readonly cargando = signal(false);

  constructor(private readonly auth: AuthService, private readonly router: Router) {}

  cerrarSesion(): void {
    if (this.cargando()) return;
    this.cargando.set(true);
    this.auth.cerrarSesion().subscribe({
      next: () => void this.router.navigate(['/login']),
      error: () => {
        // La sesión local debe terminar aunque la API de logout no responda.
        this.auth.limpiarSesion();
        void this.router.navigate(['/login']);
      },
    });
  }
}
