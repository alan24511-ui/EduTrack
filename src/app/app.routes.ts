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
import { RecuperarPassword } from './pages/recuperar-password/recuperar-password';
import { DashPapas } from './pages/dash-papas/dash-papas';
import { ConfiguracionPapas } from './pages/configuracion-papas/configuracion-papas';
import { ConfiguracionPlantel } from './pages/configuracion-plantel/configuracion-plantel';
import { Horarios } from './pages/horarios/horarios';
import { adminGuard, authGuard, tutorGuard } from './guards/role.guards';

export const routes: Routes = [
  { path: 'login', component: Login },
  { path: 'registro', component: Registro },
  { path: 'verificar-otp', component: VerificarOtp },
  { path: 'recuperar-password', component: RecuperarPassword },
  { path: 'vinculacion', component: Vinculacion, canActivate: [authGuard] },
  { path: 'dashboard', component: Dashboard, canActivate: [authGuard] },
  { path: 'estudiantes', component: Estudiantes, canActivate: [adminGuard] },
  { path: 'tarjetas', component: Tarjetas, canActivate: [adminGuard] },
  { path: 'historial', component: Historial, canActivate: [authGuard] },
  { path: 'admin', component: Admin, canActivate: [adminGuard] },
  { path: 'dashboard-papas', component: DashPapas, canActivate: [tutorGuard] },
  { path: 'configuracion-papas', component: ConfiguracionPapas, canActivate: [tutorGuard] },
  { path: 'configuracion', component: ConfiguracionPlantel, canActivate: [adminGuard] },
  { path: 'horarios', component: Horarios, canActivate: [authGuard] },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: '**', redirectTo: 'login' }
];
