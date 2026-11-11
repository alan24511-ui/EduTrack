/* FCM replaces these public values during build; no private key belongs here. */
importScripts('/runtime-config.js');
importScripts('https://www.gstatic.com/firebasejs/11.10.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/11.10.0/firebase-messaging-compat.js');

const config = self.__EDUTRACK_CONFIG__?.firebase;
if (config?.apiKey && config?.projectId && config?.messagingSenderId && config?.appId) {
  firebase.initializeApp(config);
  firebase.messaging();
}
