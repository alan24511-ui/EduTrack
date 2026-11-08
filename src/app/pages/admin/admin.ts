import { DatePipe } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { Dashboard as DashboardData, EduTrackDataService } from '../../services/edutrack-data.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-admin',
  imports: [DatePipe],
  templateUrl: './admin.html',
  styleUrl: './admin.css',
})
export class Admin implements OnInit {
  readonly datos = signal<DashboardData | null>(null);
  readonly error = signal<string | null>(null);
  readonly cargando = signal(true);

  constructor(private readonly api: EduTrackDataService) {}

  ngOnInit(): void {
    this.api.dashboard().subscribe({
      next: (data) => { this.datos.set(data); this.cargando.set(false); },
      error: (e) => { this.error.set(mensajeDeError(e)); this.cargando.set(false); },
    });
  }
}
