import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Estudiante {
  id: number;
  nombre: string;
  matricula: string;
  grupo: string;
  correoInstitucional: string | null;
  tutores?: { idTutor: number; nombre: string; parentesco: string | null; autorizado: boolean }[];
}

export interface Tarjeta {
  idTarjeta: number;
  uid: string;
  idEstudiante: number;
  nombreEstudiante: string;
  matricula: string;
  vigenciaInicio: string | null;
  vigenciaTermino: string | null;
  propietario: string | null;
  vigente: boolean;
}

export interface AsistenciaRegistro {
  id?: number;
  fecha: string;
  horaEntrada: string | null;
  horaSalida: string | null;
  asistencia?: boolean;
  estado: string;
  idEstudiante?: number;
  nombre: string;
  matricula: string;
  grupo: string;
}

export interface Dashboard {
  rol: 'administrador' | 'superadministrador' | 'tutor';
  totalEstudiantes?: number;
  tarjetasVigentes?: number;
  asistenciasHoy?: number;
  inasistencias?: number | null;
  ultimosRegistros?: AsistenciaRegistro[];
  lectores?: { nombre: string; estado: string; ultimoContacto: string | null; conectado: boolean }[];
  estudiantes?: Estudiante[];
  ultimasAsistencias?: AsistenciaRegistro[];
}

export interface DashboardTutor {
  estudiantes: Estudiante[];
  asistencias: AsistenciaRegistro[];
}

export interface HorarioPublicado {
  id: number;
  diaSemana: string;
  grupo: string;
  horaEntrada: string;
  horaSalida: string;
  tolerancia: number;
}

@Injectable({ providedIn: 'root' })
export class EduTrackDataService {
  private readonly base = environment.apiUrl;
  constructor(private readonly http: HttpClient) {}

  estudiantes(q = '', grupo = ''): Observable<Estudiante[]> {
    let params = new HttpParams();
    if (q) params = params.set('q', q);
    if (grupo) params = params.set('grupo', grupo);
    return this.http.get<Estudiante[]>(`${this.base}/estudiantes`, { params });
  }
  crearEstudiante(data: { nombre: string; matricula: string; grupo: string; correo_institucional: string | null }) {
    return this.http.post<Estudiante>(`${this.base}/estudiantes`, data);
  }
  actualizarEstudiante(id: number, data: Partial<{ nombre: string; matricula: string; grupo: string; correo_institucional: string | null }>) {
    return this.http.patch<Estudiante>(`${this.base}/estudiantes/${id}`, data);
  }
  tarjetas(uid = ''): Observable<Tarjeta[]> {
    let params = new HttpParams();
    if (uid) params = params.set('uid', uid);
    return this.http.get<Tarjeta[]>(`${this.base}/tarjetas`, { params });
  }
  crearTarjeta(data: { uid: string; id_estudiante: number; propietario: string | null; vigencia_inicio: string | null; vigencia_termino: string | null }) {
    return this.http.post<Tarjeta>(`${this.base}/tarjetas`, data);
  }
  reemplazarTarjeta(id: number, data: { uid: string; id_estudiante: number; propietario: string | null; vigencia_inicio: string | null; vigencia_termino: string | null }) {
    return this.http.put<Tarjeta>(`${this.base}/tarjetas/${id}`, data);
  }
  historial(filters: { desde?: string; hasta?: string; q?: string; grupo?: string } = {}) {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(filters)) if (value) params = params.set(key, value);
    return this.http.get<AsistenciaRegistro[]>(`${this.base}/asistencias`, { params });
  }
  dashboard() { return this.http.get<Dashboard>(`${this.base}/dashboard`); }
  dashboardTutor() { return this.http.get<DashboardTutor>(`${this.base}/tutores/dashboard`); }
  horarios() { return this.http.get<HorarioPublicado[]>(`${this.base}/horarios`); }
  crearHorario(data: Omit<HorarioPublicado, 'id'>) {
    return this.http.post<HorarioPublicado>(`${this.base}/horarios`, {
      dia_semana: data.diaSemana, grupo: data.grupo, hora_de_entrada: data.horaEntrada,
      hora_de_salida: data.horaSalida, tolerancia: data.tolerancia,
    });
  }
  actualizarHorario(id: number, data: Partial<Omit<HorarioPublicado, 'id'>>) {
    const body: Record<string, string | number> = {};
    if (data.diaSemana !== undefined) body['dia_semana'] = data.diaSemana;
    if (data.grupo !== undefined) body['grupo'] = data.grupo;
    if (data.horaEntrada !== undefined) body['hora_de_entrada'] = data.horaEntrada;
    if (data.horaSalida !== undefined) body['hora_de_salida'] = data.horaSalida;
    if (data.tolerancia !== undefined) body['tolerancia'] = data.tolerancia;
    return this.http.patch<HorarioPublicado>(`${this.base}/horarios/${id}`, body);
  }
  eliminarHorario(id: number) { return this.http.delete<void>(`${this.base}/horarios/${id}`); }
}
