
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Estudiante {
  Id_Estudiante: number;
  Matricula: string;
  Nombre: string;
  Grupo: string;
  Correo_Institucional: string | null;
}

export interface NuevoEstudiante {
  Matricula: string;
  Nombre: string;
  Grupo: string;
  Correo_Institucional?: string | null;
}

@Injectable({
  providedIn: 'root',
})
export class Api {
  private readonly http = inject(HttpClient);
  private readonly url = 'http://127.0.0.1:8000';

  obtenerEstudiantes(): Observable<Estudiante[]> {
    return this.http.get<Estudiante[]>(
      `${this.url}/estudiantes`,
    );
  }

  contarEstudiantes(): Observable<{ total: number }> {
    return this.http.get<{ total: number }>(
      `${this.url}/estudiantes/count`,
    );
  }

  crearEstudiante(
    estudiante: NuevoEstudiante,
  ): Observable<Estudiante> {
    return this.http.post<Estudiante>(
      `${this.url}/estudiantes`,
      estudiante,
    );
  }

  eliminarEstudiante(
    id: number,
  ): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(
      `${this.url}/estudiantes/${id}`,
    );
  }
}
