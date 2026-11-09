import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { inject } from '@angular/core';

import { AuthService } from '../../services/auth.service';
import { LogoutButton } from '../logout-button/logout-button';

interface ItemMenu {
  texto: string;
  icono: string;
  ruta?: string;
}

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive, LogoutButton],
  templateUrl: './sidebar.html',
  host: {
    class: 'col-12 col-md-3 col-lg-3 col-xxl-2 bg-primary text-white d-flex flex-column py-3 py-md-4',
  },
})
export class Sidebar {
  readonly auth = inject(AuthService);

  private readonly itemsAdministrador: ItemMenu[] = [
    { texto: 'Inicio', icono: 'img/v38_50.png', ruta: '/admin' },
    { texto: 'Estudiantes', icono: 'img/v38_51.png', ruta: '/estudiantes' },
    { texto: 'Tarjetas', icono: 'img/v38_52.png', ruta: '/tarjetas' },
    { texto: 'Historial', icono: 'img/v38_53.png', ruta: '/historial' },
    { texto: 'Reportes (no disponible)', icono: 'img/v38_54.png' },
    { texto: 'Horarios', icono: 'img/v38_56.png', ruta: '/horarios' },
    { texto: 'Configuración', icono: 'img/v38_55.png', ruta: '/configuracion' },
  ];

  get items(): ItemMenu[] {
    if (this.auth.rol() === 'administrador' || this.auth.rol() === 'superadministrador') return this.itemsAdministrador;
    if (this.auth.rol() === 'tutor') return [
      { texto: 'Inicio', icono: 'img/v38_50.png', ruta: '/dashboard-papas' },
      { texto: 'Vincular estudiante', icono: 'img/v38_51.png', ruta: '/vinculacion' },
      { texto: 'Historial', icono: 'img/v38_53.png', ruta: '/historial' },
      { texto: 'Horarios', icono: 'img/v38_56.png', ruta: '/horarios' },
      { texto: 'Configuración', icono: 'img/v38_55.png', ruta: '/configuracion-papas' },
    ];
    return [];
  }
}
