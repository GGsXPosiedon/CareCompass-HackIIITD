import { inspectWav } from '../src/voice/wav.ts';

export const MAX_AUDIO_BYTES = 1024 * 1024;
const json = (data, status = 200) => Response.json(data, { status, headers: { 'Cache-Control': 'no-store' } });
const languages = new Set(['en', 'hi', 'hinglish', 'auto']);
const limits = new Map();

// Best-effort per-instance protection for the prototype's paid voice routes.
function allowed(request, action) {
  const ip = request.headers.get('x-forwarded-for')?.split(',')[0] || 'local';
  const key = `${ip}:${action}`, now = Date.now();
  if (limits.size > 1000) for (const [id, item] of limits) if (item.until <= now) limits.delete(id);
  const current = limits.get(key);
  if (!current || current.until <= now) { limits.set(key, { count: 1, until: now + 60000 }); return true; }
  return ++current.count <= (action === 'transcribe' ? 12 : 30);
}

export async function handleVoice(request, env = process.env, fetcher = fetch) {
  const url = new URL(request.url);
  const origin = request.headers.get('origin');
  if (origin && origin !== url.origin) return json({ error: 'VOICE_ORIGIN_REFUSED' }, 403);
  if (request.method === 'GET') return json({ provider: env.SARVAM_API_KEY ? 'sarvam' : 'browser', maxSeconds: 25 });
  if (request.method !== 'POST') return json({ error: 'VOICE_METHOD_NOT_ALLOWED' }, 405);
  const action = url.searchParams.get('action');
  if (!['transcribe', 'speak'].includes(action) || request.headers.get('x-carecompass-voice') !== '1') return json({ error: 'INVALID_VOICE_REQUEST' }, 400);
  if (!allowed(request, action)) return json({ error: 'VOICE_RATE_LIMITED' }, 429);
  if (!env.SARVAM_API_KEY) return json({ error: 'SARVAM_NOT_CONFIGURED' }, 503);
  const language = url.searchParams.get('language') || 'auto';
  if (!languages.has(language)) return json({ error: 'INVALID_VOICE_LANGUAGE' }, 400);
  try {
    let body, endpoint;
    if (action === 'transcribe') {
      if (!request.headers.get('content-type')?.startsWith('audio/wav')) return json({ error: 'EXPECTED_WAV' }, 415);
      const bytes = new Uint8Array(await request.arrayBuffer());
      if (bytes.length > MAX_AUDIO_BYTES) return json({ error: 'VOICE_TOO_LONG' }, 413);
      let wav;
      try { wav = inspectWav(bytes); } catch { return json({ error: 'INVALID_WAV' }, 400); }
      if (wav.seconds > 26) return json({ error: 'VOICE_TOO_LONG' }, 413);
      if (wav.silent) return json({ text: '', provider: 'sarvam' });
      body = new FormData();
      body.append('file', new Blob([bytes], { type: 'audio/wav' }), 'speech.wav');
      body.append('model', env.SARVAM_STT_MODEL || 'saaras:v3');
      body.append('language_code', language === 'auto' ? 'unknown' : language === 'en' ? 'en-IN' : 'hi-IN');
      body.append('mode', language === 'hinglish' ? 'translit' : 'transcribe');
      endpoint = 'speech-to-text';
    } else {
      if (!request.headers.get('content-type')?.startsWith('application/json')) return json({ error: 'EXPECTED_JSON' }, 415);
      const raw = await request.text();
      if (raw.length > 12000) return json({ error: 'VOICE_TEXT_TOO_LONG' }, 413);
      let input;
      try { input = JSON.parse(raw); } catch { return json({ error: 'INVALID_JSON' }, 400); }
      if (typeof input.text !== 'string' || !input.text.trim() || input.text.length > 2500) return json({ error: 'INVALID_VOICE_TEXT' }, 400);
      body = JSON.stringify({ text: input.text.trim(), model: env.SARVAM_TTS_MODEL || 'bulbul:v3',
        language_code: language === 'hi' || language === 'hinglish' || /[\u0900-\u097f]/.test(input.text) ? 'hi-IN' : 'en-IN',
        speaker: env.SARVAM_SPEAKER || 'ritu', pace: 1, speech_sample_rate: 24000, output_audio_codec: 'wav' });
      endpoint = 'text-to-speech';
    }
    const headers = { 'api-subscription-key': env.SARVAM_API_KEY };
    if (action === 'speak') headers['Content-Type'] = 'application/json';
    const response = await fetcher(`https://api.sarvam.ai/${endpoint}`, { method: 'POST', headers, body,
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(25000)]) });
    if (!response.ok) return json({ error: response.status === 429 ? 'VOICE_RATE_LIMITED' : 'SARVAM_UNAVAILABLE' }, response.status === 429 ? 429 : 502);
    const data = await response.json();
    if (action === 'transcribe') {
      if (typeof data.transcript !== 'string') return json({ error: 'INVALID_SARVAM_RESPONSE' }, 502);
      return json({ text: data.transcript.trim().slice(0, 2000), provider: 'sarvam' });
    }
    const encoded = data.audios?.[0];
    if (typeof encoded !== 'string' || !encoded.length || encoded.length > 12000000 || !/^[A-Za-z0-9+/=\s]+$/.test(encoded)) return json({ error: 'INVALID_SARVAM_RESPONSE' }, 502);
    const audio = Buffer.from(encoded, 'base64');
    if (audio.length < 12 || audio.toString('ascii', 0, 4) !== 'RIFF' || audio.toString('ascii', 8, 12) !== 'WAVE') return json({ error: 'INVALID_SARVAM_AUDIO' }, 502);
    return new Response(audio, { headers: { 'Content-Type': 'audio/wav', 'Cache-Control': 'no-store' } });
  } catch (error) {
    return json({ error: error?.name === 'TimeoutError' ? 'VOICE_TIMEOUT' : 'SARVAM_UNAVAILABLE' }, error?.name === 'TimeoutError' ? 504 : 502);
  }
}
