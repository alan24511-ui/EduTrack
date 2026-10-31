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
import { adminGuard, authGuard } from './guards/role.guards';

export const routes: Routes = [
  { path: 'login', component: Login },
  { path: 'registro', component: Registro },
  { path: 'verificar-otp', component: VerificarOtp },
  { path: 'vinculacion', component: Vinculacion, canActivate: [authGuard] },
  { path: 'dashboard', component: Dashboard, canActivate: [adminGuard] },
  { path: 'estudiantes', component: Estudiantes, canActivate: [adminGuard] },
  { path: 'tarjetas', component: Tarjetas, canActivate: [adminGuard] },
  { path: 'historial', component: Historial, canActivate: [adminGuard] },
  { path: 'admin', component: Admin, canActivate: [adminGuard] },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: '**', redirectTo: 'login' }
];
