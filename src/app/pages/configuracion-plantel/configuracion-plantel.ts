import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { ConfiguracionPlantel as Plantel, ModulosService } from '../../services/modulos.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-configuracion-plantel',
  imports: [FormsModule, RouterLink],
  templateUrl: './configuracion-plantel.html',
  styleUrl: './configuracion-plantel.css',
})
export class ConfiguracionPlantel implements OnInit {
  readonly datos = signal<Plantel>({ nombre: '', direccion: '', telefono: '', correo: '', configurado: false });
  readonly error = signal<string | null>(null);
  readonly mensaje = signal<string | null>(null);
  readonly guardando = signal(false);
  constructor(readonly auth: AuthService, private readonly api: ModulosService) {}

  ngOnInit(): void {
    this.api.configuracionPlantel().subscribe({
      next: (data) => this.datos.set(data),
      error: (e: unknown) => this.error.set(mensajeDeError(e)),
    });
  }
  actualizar(campo: keyof Omit<Plantel, 'configurado'>, value: string): void {
    this.datos.update((data) => ({ ...data, [campo]: value }));
  }
  guardar(): void {
    this.error.set(null); this.mensaje.set(null); this.guardando.set(true);
    const { nombre, direccion, telefono, correo } = this.datos();
    this.api.guardarConfiguracionPlantel({ nombre, direccion, telefono, correo }).subscribe({
      next: (data) => { this.datos.set(data); this.mensaje.set('La información institucional quedó guardada y disponible.'); this.guardando.set(false); },
      error: (e: unknown) => { this.error.set(mensajeDeError(e)); this.guardando.set(false); },
    });
  }
}
