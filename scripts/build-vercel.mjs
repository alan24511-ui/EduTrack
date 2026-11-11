import { spawnSync } from 'node:child_process';
import { readFile, writeFile } from 'node:fs/promises';

const configFile = new URL('../public/runtime-config.js', import.meta.url);
const placeholder = await readFile(configFile, 'utf8');
const apiUrl = process.env.EDUTRACK_API_URL?.trim();
const firebase = {
  apiKey: process.env.FIREBASE_WEB_API_KEY?.trim() || '',
  authDomain: process.env.FIREBASE_WEB_AUTH_DOMAIN?.trim() || '',
  projectId: process.env.FIREBASE_WEB_PROJECT_ID?.trim() || '',
  storageBucket: process.env.FIREBASE_WEB_STORAGE_BUCKET?.trim() || '',
  messagingSenderId: process.env.FIREBASE_WEB_MESSAGING_SENDER_ID?.trim() || '',
  appId: process.env.FIREBASE_WEB_APP_ID?.trim() || '',
  vapidKey: process.env.FIREBASE_WEB_VAPID_KEY?.trim() || '',
};

if (!apiUrl) {
  console.error('Falta EDUTRACK_API_URL (URL pública de FastAPI) en el entorno de compilación.');
  process.exit(1);
}

let parsedUrl;
try {
  parsedUrl = new URL(apiUrl);
} catch {
  console.error('EDUTRACK_API_URL debe ser una URL absoluta HTTP o HTTPS.');
  process.exit(1);
}
if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
  console.error('EDUTRACK_API_URL debe usar HTTP o HTTPS.');
  process.exit(1);
}

try {
  await writeFile(
    configFile,
    `window.__EDUTRACK_CONFIG__ = ${JSON.stringify({ apiUrl: parsedUrl.origin + parsedUrl.pathname.replace(/\/$/, ''), firebase })};\n`,
    'utf8',
  );
  const result = spawnSync('npx', ['ng', 'build', '--configuration', 'production'], {
    stdio: 'inherit',
    shell: process.platform === 'win32',
  });
  process.exitCode = result.status ?? 1;
} finally {
  await writeFile(configFile, placeholder, 'utf8');
}
