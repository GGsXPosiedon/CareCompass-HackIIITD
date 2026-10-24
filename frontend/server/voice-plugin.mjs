import { handleVoice, MAX_AUDIO_BYTES } from './sarvam.mjs';

export function voicePlugin(env, fetcher = fetch) {
  const setup = server => { server.middlewares.use(async (req, res, next) => {
    if (new URL(req.url || '/', 'http://localhost').pathname !== '/api/voice') return next();
    const controller = new AbortController();
    res.on('close', () => { if (!res.writableEnded) controller.abort(); });
    try {
      const chunks = []; let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > MAX_AUDIO_BYTES) { res.statusCode = 413; res.end('{"error":"VOICE_TOO_LONG"}'); return; }
        chunks.push(chunk);
      }
      const request = new Request(`http://${req.headers.host}${req.url}`, { method: req.method, headers: req.headers,
        ...(size ? { body: Buffer.concat(chunks) } : {}), signal: controller.signal });
      const response = await handleVoice(request, env, fetcher);
      res.statusCode = response.status;
      response.headers.forEach((value, key) => res.setHeader(key, value));
      res.end(Buffer.from(await response.arrayBuffer()));
    } catch { res.statusCode = 500; res.end('{"error":"VOICE_SERVER_ERROR"}'); }
  }); };
  return { name: 'carecompass-sarvam-voice', configureServer: setup, configurePreviewServer: setup };
}
