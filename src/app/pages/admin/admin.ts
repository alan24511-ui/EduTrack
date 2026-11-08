import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Sidebar } from '../../components/sidebar/sidebar';
import { Component, OnInit, signal } from '@angular/core';
import { Dashboard as DashboardData, EduTrackDataService } from '../../services/edutrack-data.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-admin',
  imports: [DatePipe, FormsModule, Sidebar],
  templateUrl: './admin.html',
})
export class Admin implements OnInit {
  readonly datos = signal<DashboardData | null>(null);
  readonly error = signal<string | null>(null);
  readonly cargando = signal(true);
  buscar = '';

  get registrosVisibles() {
    const query = this.buscar.trim().toLocaleLowerCase();
    return (this.datos()?.ultimosRegistros ?? []).filter((registro) =>
      !query || [registro.nombre, registro.matricula, registro.grupo, registro.estado]
        .some((valor) => valor?.toLocaleLowerCase().includes(query)),
    );
  }

  constructor(private readonly api: EduTrackDataService) {}

  ngOnInit(): void {
    this.api.dashboard().subscribe({
      next: (data) => { this.datos.set(data); this.cargando.set(false); },
      error: (e) => { this.error.set(mensajeDeError(e)); this.cargando.set(false); },
    });
  }
}
