import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

interface ItemMenu {
  texto: string;
  icono: string;
  ruta?: string;
}

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './sidebar.html',
  host: {
    class: 'col-12 col-md-4 col-lg-3 col-xxl-2 bg-primary text-white d-flex flex-column py-3 py-md-4',
  },
})
export class Sidebar {
  // Reportes y Configuración todavía no tienen ruta.
  readonly items: ItemMenu[] = [
    { texto: 'Inicio', icono: 'img/v38_50.png', ruta: '/admin' },
    { texto: 'Estudiantes', icono: 'img/v38_51.png', ruta: '/estudiantes' },
    { texto: 'Tarjetas', icono: 'img/v38_52.png', ruta: '/tarjetas' },
    { texto: 'Historial', icono: 'img/v38_53.png', ruta: '/historial' },
    { texto: 'Reportes', icono: 'img/v38_54.png' },
    { texto: 'Configuración', icono: 'img/v38_55.png' },
  ];
}