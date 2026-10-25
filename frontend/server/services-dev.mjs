import { createServer } from 'node:http';
import { createServer as createViteServer, loadEnv } from 'vite';
import care from '../api/care.mjs';
import { handleVoice } from './sarvam.mjs';

// vercel dev's Vite service runner does not dispatch api/ functions itself.
// Run those handlers here, with the same runtime binding injected into this process.
const env = { ...loadEnv('services', process.cwd(), ''), ...process.env };
const vite = await createViteServer({ mode: 'services', configLoader: 'native', server: { middlewareMode: true, hmr: false } });
const server = createServer(async (req, res) => {
  // The local Vercel gateway changes Host when forwarding to the service port.
  const host = req.headers['x-forwarded-host'] || req.headers.host;
  const protocol = req.headers['x-forwarded-proto'] || 'http';
  const url = new URL(req.url || '/', `${protocol}://${host}`);
  if (!url.pathname.startsWith('/api/')) return vite.middlewares(req, res);
  const controller = new AbortController();
  res.on('close', () => { if (!res.writableEnded) controller.abort(); });
  try {
    const chunks = []; let size = 0;
    for await (const chunk of req) {
      size += chunk.length;
      if (size > 1024 * 1024) { res.writeHead(413); res.end(); return; }
      chunks.push(chunk);
    }
    const request = new Request(url, { method: req.method, headers: req.headers, signal: controller.signal,
      ...(size ? { body: Buffer.concat(chunks) } : {}) });
    const response = url.pathname === '/api/voice' ? await handleVoice(request, env) : await care.fetch(request);
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch { res.writeHead(500); res.end('{"error":"DEV_SERVER_ERROR"}'); }
});
server.listen(Number(process.env.PORT || 3000), '127.0.0.1');
async function close() { server.closeAllConnections(); server.close(); await vite.close(); }
process.once('SIGINT', close);
process.once('SIGTERM', close);
