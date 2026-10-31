import { Routes } from '@angular/router';

import { Login } from './pages/login/login';
import { Registro } from './pages/registro/registro';
import { VerificarOtp } from './pages/verificar-otp/verificar-otp';
import { Vinculacion } from './pages/vinculacion/vinculacion';
import { Dashboard } from './pages/dashboard/dashboard';
import { Estudiantes } from './pages/estudiantes/estudiantes';
import { Tarjetas } from './pages/tarjetas/tarjetas';
import { Historial } from './pages/historial/historial';
import { Admin } from './pages/admin/admin';

export const routes: Routes = [
  { path: 'login', component: Login },
  { path: 'registro', component: Registro },
  { path: 'verificar-otp', component: VerificarOtp },
  { path: 'vinculacion', component: Vinculacion },
  { path: 'dashboard', component: Dashboard },
  { path: 'estudiantes', component: Estudiantes },
  { path: 'tarjetas', component: Tarjetas },
  { path: 'historial', component: Historial },
  { path: 'admin', component: Admin },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: '**', redirectTo: 'login' }
];
