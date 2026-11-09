import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';

export interface EstudianteVinculacion {
  nombre: string;
  grupo: string;
  matricula: string;
}

export interface RespuestaConsulta {
  estudiante: EstudianteVinculacion;
}

export interface RespuestaConfirmacion {
  mensaje: string;
  idTutor: number;
}

@Injectable({ providedIn: 'root' })
export class VinculacionService {
  private readonly apiUrl = `${environment.apiUrl}/vinculacion`;

  constructor(private readonly http: HttpClient) {}

  /** Valida un código y devuelve nombre, grupo y matrícula del estudiante. */
  consultar(codigo: string): Observable<RespuestaConsulta> {
    return this.http.post<RespuestaConsulta>(`${this.apiUrl}/consultar`, { codigo });
  }

  /** Consume el código y crea la relación en Estudiante_Tutor. */
  confirmar(codigo: string, parentesco: string): Observable<RespuestaConfirmacion> {
    return this.http.post<RespuestaConfirmacion>(`${this.apiUrl}/confirmar`, {
      codigo,
      parentesco,
    });
  }
}
