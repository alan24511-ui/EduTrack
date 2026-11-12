import { Injectable, NgZone, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../environments/environment';

interface FirebaseMessagingCompat {
  getToken(options: { vapidKey: string; serviceWorkerRegistration: ServiceWorkerRegistration }): Promise<string>;
  onMessage(callback: (payload: { notification?: { title?: string; body?: string }; data?: Record<string, string> }) => void): () => void;
}

declare global {
  interface Window {
    firebase?: {
      apps: unknown[];
      initializeApp(config: NonNullable<typeof environment.firebase>): unknown;
      messaging: (() => FirebaseMessagingCompat) & { isSupported(): boolean | Promise<boolean> };
    };
  }
}

export type EstadoPermisoPush = 'no_configurado' | 'no_disponible' | 'denegado' | 'registrado' | 'error';

@Injectable({ providedIn: 'root' })
export class PushNotificationsService {
  private readonly http = inject(HttpClient);
  private readonly zone = inject(NgZone);
  readonly estado = signal<EstadoPermisoPush>('no_configurado');
  readonly mensajeRecibido = signal<{ title?: string; body?: string; data?: Record<string, string> } | null>(null);
  private messaging?: FirebaseMessagingCompat;
  private listening = false;

  /** Refresca el token sin pedir permiso si el tutor ya lo había autorizado. */
  actualizarTokenSiPermitido(): void {
    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
      void this.habilitarEnEsteDispositivo();
    }
  }

  /** Debe invocarse desde una acción explícita del tutor para mostrar el prompt del navegador. */
  async habilitarEnEsteDispositivo(): Promise<EstadoPermisoPush> {
    const config = environment.firebase;
    if (!config?.apiKey || !config.projectId || !config.messagingSenderId || !config.appId || !config.vapidKey) {
      this.estado.set('no_configurado');
      return this.estado();
    }
    if (typeof window === 'undefined' || !('Notification' in window) || !('serviceWorker' in navigator)) {
      this.estado.set('no_disponible');
      return this.estado();
    }
    if (Notification.permission === 'denied') {
      this.estado.set('denegado');
      return this.estado();
    }
    try {
      const permisoSolicitado = Notification.permission === 'granted'
        ? Promise.resolve<NotificationPermission>('granted')
        : Notification.requestPermission();
      const permiso = await permisoSolicitado;
      if (permiso !== 'granted') {
        this.estado.set('denegado');
        return this.estado();
      }
      if (!window.firebase || !(await window.firebase.messaging.isSupported())) {
        this.estado.set('no_disponible');
        return this.estado();
      }
      if (!window.firebase.apps.length) window.firebase.initializeApp(config);
      this.messaging = window.firebase.messaging();
      const sw = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
      const token = await this.messaging.getToken({ vapidKey: config.vapidKey, serviceWorkerRegistration: sw });
      if (!token) throw new Error('Firebase no devolvió un token para este dispositivo.');
      await firstValueFrom(this.http.put(`${environment.apiUrl}/notificaciones/dispositivo`, { token }));
      this.estado.set('registrado');
      this.escucharPrimerPlano();
      return this.estado();
    } catch (error) {
      this.estado.set('error');
      console.warn('No fue posible activar las notificaciones push.', error);
      return this.estado();
    }
  }

  async deshabilitarEnEsteDispositivo(): Promise<void> {
    try {
      const config = environment.firebase;
      if (!config?.apiKey || !config.projectId || !config.messagingSenderId || !config.appId || !config.vapidKey) return;
      if (!this.messaging && window.firebase && await window.firebase.messaging.isSupported()) {
        if (!window.firebase.apps.length) window.firebase.initializeApp(config);
        this.messaging = window.firebase.messaging();
      }
      if (!this.messaging) return;
      const sw = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
      const token = await this.messaging.getToken({ vapidKey: config.vapidKey, serviceWorkerRegistration: sw });
      if (token) await firstValueFrom(this.http.delete(`${environment.apiUrl}/notificaciones/dispositivo`, { body: { token } }));
      this.estado.set('no_disponible');
    } catch (error) {
      this.estado.set('error');
      console.warn('No fue posible desactivar este dispositivo.', error);
    }
  }

  private escucharPrimerPlano(): void {
    if (!this.messaging || this.listening) return;
    this.listening = true;
    this.messaging.onMessage((payload) => this.zone.run(() => {
      this.mensajeRecibido.set({
        title: payload.notification?.title,
        body: payload.notification?.body,
        data: payload.data,
      });
    }));
  }
}
