import { Routes } from '@angular/router';
import { adminGuard, authGuard, inicioGuard, tutorGuard } from './guards/role.guards';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./pages/login/login').then((m) => m.Login) },
  { path: 'registro', loadComponent: () => import('./pages/registro/registro').then((m) => m.Registro) },
  { path: 'verificar-otp', loadComponent: () => import('./pages/verificar-otp/verificar-otp').then((m) => m.VerificarOtp) },
  { path: 'recuperar-password', loadComponent: () => import('./pages/recuperar-password/recuperar-password').then((m) => m.RecuperarPassword) },
  { path: 'vinculacion', loadComponent: () => import('./pages/vinculacion/vinculacion').then((m) => m.Vinculacion), canActivate: [authGuard] },
  { path: 'dashboard', loadComponent: () => import('./pages/dashboard/dashboard').then((m) => m.Dashboard), canActivate: [authGuard] },
  { path: 'estudiantes', loadComponent: () => import('./pages/estudiantes/estudiantes').then((m) => m.Estudiantes), canActivate: [adminGuard] },
  { path: 'tarjetas', loadComponent: () => import('./pages/tarjetas/tarjetas').then((m) => m.Tarjetas), canActivate: [adminGuard] },
  { path: 'historial', loadComponent: () => import('./pages/historial/historial').then((m) => m.Historial), canActivate: [authGuard] },
  { path: 'admin', loadComponent: () => import('./pages/admin/admin').then((m) => m.Admin), canActivate: [adminGuard] },
  { path: 'dashboard-papas', loadComponent: () => import('./pages/dash-papas/dash-papas').then((m) => m.DashPapas), canActivate: [tutorGuard] },
  { path: 'configuracion-papas', loadComponent: () => import('./pages/configuracion-papas/configuracion-papas').then((m) => m.ConfiguracionPapas), canActivate: [tutorGuard] },
  { path: 'configuracion', loadComponent: () => import('./pages/configuracion-plantel/configuracion-plantel').then((m) => m.ConfiguracionPlantel), canActivate: [adminGuard] },
  { path: 'horarios', loadComponent: () => import('./pages/horarios/horarios').then((m) => m.Horarios), canActivate: [authGuard] },
  { path: '', loadComponent: () => import('./pages/login/login').then((m) => m.Login), canActivate: [inicioGuard], pathMatch: 'full' },
  { path: '**', redirectTo: '' },
];
