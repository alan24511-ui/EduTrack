import { Component, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Sidebar } from '../../components/sidebar/sidebar';
import { AuthService } from '../../services/auth.service';
import { DashboardTutor, EduTrackDataService } from '../../services/edutrack-data.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-dash-papas',
  imports: [DatePipe, Sidebar],
  templateUrl: './dash-papas.html',
})
export class DashPapas implements OnInit {
  readonly datos = signal<DashboardTutor | null>(null);
  readonly error = signal<string | null>(null);
  readonly cargando = signal(true);
  constructor(readonly auth: AuthService, private readonly api: EduTrackDataService) {}

  ngOnInit(): void {
    this.api.dashboardTutor().subscribe({
      next: (data) => { this.datos.set(data); this.cargando.set(false); },
      error: (error: unknown) => { this.error.set(mensajeDeError(error)); this.cargando.set(false); },
    });
  }
  iniciales(nombre: string | undefined): string {
    return (nombre ?? '').split(/\s+/).filter(Boolean).slice(0, 2).map((parte) => parte[0]).join('').toUpperCase();
  }
}
