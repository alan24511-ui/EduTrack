import { Component, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Layout } from '../../components/layout/layout';
import { Dashboard as DashboardData, EduTrackDataService } from '../../services/edutrack-data.service';
import { mensajeDeError } from '../../utils/errores';
import { AuthService } from '../../services/auth.service';

@Component({
  imports: [Layout, RouterLink, DatePipe],
  selector: 'app-dashboard',
  templateUrl: './dashboard.html',
})
export class Dashboard implements OnInit {
  readonly datos = signal<DashboardData | null>(null);
  readonly error = signal<string | null>(null);
  readonly cargando = signal(true);
  constructor(private readonly api: EduTrackDataService, readonly auth: AuthService) {}

  ngOnInit(): void {
    this.api.dashboard().subscribe({
      next: (data) => { this.datos.set(data); this.cargando.set(false); },
      error: (e) => { this.error.set(mensajeDeError(e)); this.cargando.set(false); },
    });
  }
}
