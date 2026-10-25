import { createServer } from 'node:http';
import { voicePlugin } from './voice-plugin.mjs';

if (!process.env.VOICE_PUBLIC_ORIGIN) throw new Error('Set VOICE_PUBLIC_ORIGIN to the public HTTPS origin.');
const origin = new URL(process.env.VOICE_PUBLIC_ORIGIN);
if (origin.protocol !== 'https:' || origin.origin !== process.env.VOICE_PUBLIC_ORIGIN) {
  throw new Error('VOICE_PUBLIC_ORIGIN must be an HTTPS origin without a trailing slash or path.');
}

// Reuse the bounded voice adapter used in local development.
voicePlugin(process.env).configureServer({ middlewares: { use(handler) {
  const server = createServer((req, res) => handler(req, res, () => {
    res.writeHead(404); res.end();
  }));
  server.requestTimeout = 35000;
  server.headersTimeout = 10000;
  server.listen(Number(process.env.VOICE_PORT || 3001), '127.0.0.1');
} } });
