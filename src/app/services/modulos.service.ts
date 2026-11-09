import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

export interface PreferenciasTutor { notificacionesHabilitadas: boolean; }
export interface ConfiguracionPlantel {
  nombre: string;
  direccion: string;
  telefono: string;
  correo: string;
  configurado: boolean;
}

@Injectable({ providedIn: 'root' })
export class ModulosService {
  private readonly base = environment.apiUrl;
  constructor(private readonly http: HttpClient) {}

  preferenciasTutor() { return this.http.get<PreferenciasTutor>(`${this.base}/tutores/me/preferencias`); }
  guardarPreferenciasTutor(preferencias: PreferenciasTutor) {
    return this.http.put<PreferenciasTutor>(`${this.base}/tutores/me/preferencias`, preferencias);
  }
  configuracionPlantel() { return this.http.get<ConfiguracionPlantel>(`${this.base}/configuracion/plantel`); }
  guardarConfiguracionPlantel(data: Omit<ConfiguracionPlantel, 'configurado'>) {
    return this.http.put<ConfiguracionPlantel>(`${this.base}/configuracion/plantel`, data);
  }
}
