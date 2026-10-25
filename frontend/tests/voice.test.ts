import test from 'node:test';
import assert from 'node:assert/strict';
import { encodeWav, inspectWav } from '../src/voice/wav.ts';
import { handleVoice } from '../server/sarvam.mjs';
import voiceFunction from '../api/voice.mjs';
import { recordStream, registerVoiceStop, stopAllVoice } from '../src/voice/client.ts';
import { voicePlugin } from '../server/voice-plugin.mjs';
import { createServer } from 'node:http';
import { primeVoicePlayback, scheduleResponseVoice, voicePlaybackContext } from '../src/voice/playback.ts';

const env = { SARVAM_API_KEY: 'unit-test-secret-not-a-real-key' };
let sequence = 0;
function request(action: string, language = 'en', body: BodyInit = JSON.stringify({ text: 'A plain care explanation.' })) {
  return new Request(`https://care.example/api/voice?action=${action}&language=${language}`, {
    method: 'POST', headers: { 'x-carecompass-voice': '1', 'x-forwarded-for': `test-${sequence++}`,
      'content-type': action === 'transcribe' ? 'audio/wav' : 'application/json', origin: 'https://care.example' }, body,
  });
}
const wave = (seconds = 1, silent = false) => encodeWav(Float32Array.from({ length: 48000 * seconds }, (_, i) => silent ? 0 : Math.sin(i / 20) * .1), 48000);

test('recorded audio becomes bounded mono PCM16 at 16kHz; silence is detected', () => {
  const wav = wave();
  assert.equal(wav.byteLength, 32044);
  assert.deepEqual(inspectWav(new Uint8Array(wav)), { seconds: 1, silent: false });
  assert.equal(inspectWav(new Uint8Array(wave(1, true))).silent, true);
  assert.throws(() => inspectWav(new Uint8Array(44)));
  assert.throws(() => encodeWav(new Float32Array(10), 0));
});

test('cloud configuration reveals availability but never the subscription key', async () => {
  const response = await handleVoice(new Request('https://care.example/api/voice'), env);
  assert.deepEqual(await response.json(), { provider: 'sarvam', maxSeconds: 25 });
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal((await handleVoice(new Request('https://care.example/api/voice'), {})).status, 200);
  assert.equal((await handleVoice(request('speak'), {})).status, 503);
  // The deployed function uses the same handler and requires no Python route.
  assert.equal((await voiceFunction.fetch(new Request('https://care.example/api/voice'))).status, 200);
});

test('Sarvam STT forwards valid WAV and the intended English, Hindi, Hinglish and auto modes', async () => {
  for (const [language, code, mode] of [['en', 'en-IN', 'transcribe'], ['hi', 'hi-IN', 'transcribe'], ['hinglish', 'hi-IN', 'translit'], ['auto', 'unknown', 'transcribe']]) {
    let called = false;
    const response = await handleVoice(request('transcribe', language, wave()), env, async (url, init) => {
      called = true;
      assert.equal(url, 'https://api.sarvam.ai/speech-to-text');
      assert.equal(init.headers['api-subscription-key'], env.SARVAM_API_KEY);
      assert.equal(init.body.get('language_code'), code);
      assert.equal(init.body.get('mode'), mode);
      assert.equal(init.body.get('model'), 'saaras:v3');
      assert.equal(init.body.get('file').type, 'audio/wav');
      return Response.json({ transcript: '  papa ko bukhar hai  ' });
    });
    assert.ok(called); assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { text: 'papa ko bukhar hai', provider: 'sarvam' });
  }
});

test('silence, invalid WAV and overlong clips never reach a paid provider', async () => {
  const never = async () => { throw new Error('provider should not be called'); };
  const silent = await handleVoice(request('transcribe', 'hi', wave(1, true)), env, never);
  assert.equal(silent.status, 200); assert.equal((await silent.json()).text, '');
  assert.equal((await handleVoice(request('transcribe', 'en', new Uint8Array(100)), env, never)).status, 400);
  assert.equal((await handleVoice(request('transcribe', 'en', wave(27)), env, never)).status, 413);
});
test('Hindi speech stays in the original script and never requests translation', async () => {
  const transcript = 'पापा को दो दिन से बुखार है';
  const response = await handleVoice(request('transcribe', 'auto', wave()), env, async (_url, init) => {
    assert.equal(init.body.get('language_code'), 'unknown');
    assert.equal(init.body.get('mode'), 'transcribe');
    return Response.json({ transcript, language_code: 'hi-IN' });
  });
  assert.equal((await response.json()).text, transcript);
});

test('Sarvam TTS uses Bulbul, Indian language voices, and returns decoded WAV bytes', async () => {
  const wav = Buffer.from(wave(.1));
  const response = await handleVoice(request('speak', 'hinglish'), env, async (url, init) => {
    assert.equal(url, 'https://api.sarvam.ai/text-to-speech');
    const body = JSON.parse(init.body);
    assert.equal(body.language_code, 'hi-IN'); assert.equal(body.speaker, 'ritu'); assert.equal(body.model, 'bulbul:v3');
    assert.equal(body.speech_sample_rate, 24000);
    assert.ok(!url.includes(env.SARVAM_API_KEY)); assert.ok(!init.body.includes(env.SARVAM_API_KEY));
    return Response.json({ audios: [wav.toString('base64')] });
  });
  assert.equal(response.headers.get('content-type'), 'audio/wav');
  assert.deepEqual(Buffer.from(await response.arrayBuffer()), wav);
});

test('voice routes reject cross-origin traffic, unsupported languages, oversized text and malformed JSON', async () => {
  const cross = request('speak'); cross.headers.set('origin', 'https://other.example');
  assert.equal((await handleVoice(cross, env)).status, 403);
  assert.equal((await handleVoice(request('speak', 'unknown-language'), env)).status, 400);
  assert.equal((await handleVoice(request('speak', 'en', '{'), env)).status, 400);
  assert.equal((await handleVoice(request('speak', 'en', JSON.stringify({ text: 'x'.repeat(2501) })), env)).status, 400);
  const missingHeader = request('speak'); missingHeader.headers.delete('x-carecompass-voice');
  assert.equal((await handleVoice(missingHeader, env)).status, 400);
});

test('provider outages and bad responses are explicit and do not expose provider payloads or credentials', async () => {
  const failure = await handleVoice(request('speak'), env, async () => Response.json({ leaked: env.SARVAM_API_KEY }, { status: 401 }));
  assert.equal(failure.status, 502); assert.ok(!(await failure.text()).includes(env.SARVAM_API_KEY));
  assert.equal((await handleVoice(request('speak'), env, async () => Response.json({ audios: ['not audio'] }))).status, 502);
  assert.equal((await handleVoice(request('transcribe', 'en', wave()), env, async () => Response.json({}))).status, 502);
  assert.equal((await handleVoice(request('speak'), env, async () => new Response('', { status: 429 }))).status, 429);
});

test('navigation stop registry cancels recording and playback and releases listeners', () => {
  let count = 0;
  const first = registerVoiceStop(() => count++), second = registerVoiceStop(() => count++);
  stopAllVoice(); assert.equal(count, 2); first(); second(); stopAllVoice(); assert.equal(count, 2);
});

test('recorder cancellation releases every microphone track without decoding or sending', () => {
  const original = Object.getOwnPropertyDescriptor(globalThis, 'MediaRecorder');
  class FakeRecorder {
    static isTypeSupported() { return true; }
    state = 'inactive'; ondataavailable = null; onerror = null; onstop = null;
    start() { this.state = 'recording'; }
    stop() { this.state = 'inactive'; this.onstop?.(); }
  }
  Object.defineProperty(globalThis, 'MediaRecorder', { value: FakeRecorder, configurable: true });
  let released = 0;
  try {
    const recording = recordStream({ getTracks: () => [{ stop: () => released++ }] } as unknown as MediaStream, () => {});
    recording.cancel(); assert.equal(released, 1);
  } finally { if (original) Object.defineProperty(globalThis, 'MediaRecorder', original); else Reflect.deleteProperty(globalThis, 'MediaRecorder'); }
});

test('the Vite voice middleware serves config, transcription and audio before the care API proxy', async () => {
  let middleware;
  const plugin = voicePlugin({ ...env, VOICE_PUBLIC_ORIGIN: 'https://care.example' }, async url => url.endsWith('speech-to-text')
    ? Response.json({ transcript: 'Need a sample collection tomorrow' })
    : Response.json({ audios: [Buffer.from(wave(.1)).toString('base64')] }));
  assert.equal(plugin.configureServer({ middlewares: { use: fn => { middleware = fn; return {}; } } }), undefined);
  const server = createServer((req, res) => middleware(req, res, () => { res.statusCode = 404; res.end(); }));
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  assert.ok(address && typeof address !== 'string');
  const base = `http://127.0.0.1:${address.port}/api/voice`;
  try {
    assert.equal((await (await fetch(base)).json()).provider, 'sarvam');
    assert.equal((await fetch(base, { headers: { origin: 'https://care.example' } })).status, 200);
    assert.equal((await fetch(base, { headers: { origin: 'https://other.example' } })).status, 403);
    const result = await fetch(`${base}?action=transcribe&language=hinglish`, { method: 'POST',
      headers: { origin: 'https://care.example', 'content-type': 'audio/wav', 'x-carecompass-voice': '1' }, body: wave() });
    assert.equal((await result.json()).text, 'Need a sample collection tomorrow');
    const audio = await fetch(`${base}?action=speak&language=en`, { method: 'POST',
      headers: { 'content-type': 'application/json', 'x-carecompass-voice': '1' }, body: JSON.stringify({ text: 'Please review this recommendation.' }) });
    assert.equal(audio.headers.get('content-type'), 'audio/wav');
    assert.equal((await audio.arrayBuffer()).byteLength, 3244);
  } finally { server.closeAllConnections(); await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve())); }
});


test('automatic voice survives discarded effects, speaks each response once, and cancels before unmount', async () => {
  const first = {}, second = {}, removed = {};
  const spoken: object[] = [];
  const discard = scheduleResponseVoice(first, () => spoken.push(first));
  discard(); // React StrictMode discards its first setup.
  scheduleResponseVoice(first, () => spoken.push(first));
  await Promise.resolve();
  scheduleResponseVoice(first, () => spoken.push(first)); // Rerender or return to an old response.
  scheduleResponseVoice(second, () => spoken.push(second));
  const unmount = scheduleResponseVoice(removed, () => spoken.push(removed));
  unmount();
  await Promise.resolve();
  assert.deepEqual(spoken, [first, second]);
});

test('the send gesture resumes one shared audio context reused by later responses', () => {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'window');
  let contexts = 0, resumes = 0;
  class FakeContext {
    state = 'suspended';
    constructor() { contexts++; }
    resume() { resumes++; this.state = 'running'; return Promise.resolve(); }
  }
  Object.defineProperty(globalThis, 'window', { configurable: true, value: { AudioContext: FakeContext } });
  try {
    const first = primeVoicePlayback();
    assert.equal(voicePlaybackContext(), first);
    assert.equal(primeVoicePlayback(), first);
    assert.equal(contexts, 1); assert.equal(resumes, 1);
    (first as unknown as FakeContext).state = 'suspended';
    primeVoicePlayback();
    assert.equal(resumes, 2);
    (first as unknown as FakeContext).state = 'closed';
    assert.notEqual(primeVoicePlayback(), first);
    assert.equal(contexts, 2);
  } finally {
    if (previous) Object.defineProperty(globalThis, 'window', previous);
    else Reflect.deleteProperty(globalThis, 'window');
  }
});
