import { isDevMode } from '@angular/core';

declare global {
  interface Window {
    __EDUTRACK_CONFIG__?: {
      apiUrl?: string;
      firebase?: {
        apiKey?: string;
        authDomain?: string;
        projectId?: string;
        storageBucket?: string;
        messagingSenderId?: string;
        appId?: string;
        vapidKey?: string;
      };
    };
  }
}

const development = isDevMode();

export const environment = {
  production: !development,
  // runtime-config.js solo contiene esta URL pública; las credenciales nunca van en Angular.
  apiUrl: window.__EDUTRACK_CONFIG__?.apiUrl || (development ? 'http://localhost:8000' : ''),
  firebase: window.__EDUTRACK_CONFIG__?.firebase,
};
