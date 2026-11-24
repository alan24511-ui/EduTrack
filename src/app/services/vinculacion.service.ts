import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';

export interface EstudianteVinculacion {
  id: number;
  nombre: string;
  grupo: string;
  matricula: string;
}

export interface RespuestaBusqueda {
  grupos: string[];
  estudiantes: EstudianteVinculacion[];
}

export interface RespuestaConfirmacion {
  mensaje: string;
}

@Injectable({ providedIn: 'root' })
export class VinculacionService {
  private readonly apiUrl = `${environment.apiUrl}/vinculacion`;

  constructor(private readonly http: HttpClient) {}

  buscar(q: string, grupo: string): Observable<RespuestaBusqueda> {
    let params = new HttpParams().set('q', q);
    if (grupo) params = params.set('grupo', grupo);
    return this.http.get<RespuestaBusqueda>(`${this.apiUrl}/buscar`, { params });
  }

  confirmar(idEstudiante: number, parentesco: string): Observable<RespuestaConfirmacion> {
    return this.http.post<RespuestaConfirmacion>(`${this.apiUrl}/confirmar`, {
      id_estudiante: idEstudiante,
      parentesco,
    });
  }
}
