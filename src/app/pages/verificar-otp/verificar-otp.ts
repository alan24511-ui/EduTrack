import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../services/auth.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-verificar-otp',
  imports: [FormsModule, RouterLink],
  templateUrl: './verificar-otp.html',
})
export class VerificarOtp implements OnInit {
  correo = '';
  token = '';

  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly aviso = signal<string | null>(null);

  constructor(
    private readonly auth: AuthService,
    private readonly router: Router,
    private readonly ruta: ActivatedRoute,
  ) {}

  ngOnInit(): void {
    this.correo = this.ruta.snapshot.queryParamMap.get('correo') ?? '';
  }

  verificar(): void {
    this.error.set(null);
    this.cargando.set(true);

    this.auth.verificarOtp(this.correo, this.token.trim()).subscribe({
      next: () => {
        this.cargando.set(false);
        this.router.navigate(['/vinculacion']);
      },
      error: (error) => {
        this.cargando.set(false);
        this.error.set(mensajeDeError(error));
      },
    });
  }

  reenviar(): void {
    this.error.set(null);
    this.aviso.set(null);
    this.cargando.set(true);
    this.auth.reenviarOtp(this.correo).subscribe({
      next: (respuesta) => { this.cargando.set(false); this.aviso.set(respuesta.mensaje); },
      error: (error) => { this.cargando.set(false); this.error.set(mensajeDeError(error)); },
    });
  }
}
