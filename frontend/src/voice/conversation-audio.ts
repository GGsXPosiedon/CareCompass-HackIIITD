import type { Language } from '../types';
import { recordStream, supportsRecording, synthesize, transcribe, voiceConfig } from './client.ts';
import { TurnSilence } from './conversation.ts';
import { voicePlaybackContext } from './playback.ts';

function aborted() { return new DOMException('Voice session ended', 'AbortError'); }
export async function listenForTurn(language: Language, signal: AbortSignal, ready: (finish: (() => void) | null) => void): Promise<string> {
  const config = await voiceConfig();
  signal.throwIfAborted();
  if (config.provider !== 'sarvam') return browserListen(language, signal, ready);
  if (!supportsRecording()) throw new Error('MICROPHONE_UNSUPPORTED');
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
  if (signal.aborted) { stream.getTracks().forEach(track => track.stop()); throw aborted(); }
  const context = voicePlaybackContext();
  if (!context || context.state !== 'running') { stream.getTracks().forEach(track => track.stop()); throw new Error('AUDIO_BLOCKED'); }
  let input: MediaStreamAudioSourceNode;
  try { input = context.createMediaStreamSource(stream); }
  catch (error) { stream.getTracks().forEach(track => track.stop()); throw error; }
  const analyser = context.createAnalyser(); analyser.fftSize = 2048; input.connect(analyser);
  const samples = new Float32Array(analyser.fftSize), detector = new TurnSilence();
  let finish!: () => void, quiet = false, settled = false;
  let recording: ReturnType<typeof recordStream>;
  try { recording = recordStream(stream, () => finish()); }
  catch (error) { input.disconnect(); analyser.disconnect(); throw error; }
  const done = new Promise<Blob>((resolve, reject) => {
    let timer: ReturnType<typeof setInterval>;
    const release = () => { clearInterval(timer); input.disconnect(); analyser.disconnect(); signal.removeEventListener('abort', cancel); ready(null); };
    const cancel = () => { if (settled) return; settled = true; release(); recording.cancel(); reject(aborted()); };
    finish = () => {
      if (settled) return; settled = true; release();
      void recording.stop().then(resolve, reject);
    };
    signal.addEventListener('abort', cancel, { once: true });
    const started = performance.now();
    timer = setInterval(() => {
      analyser.getFloatTimeDomainData(samples);
      const rms = Math.sqrt(samples.reduce((sum, sample) => sum + sample * sample, 0) / samples.length);
      const turn = detector.sample(rms, performance.now() - started);
      if (turn === 'quiet') quiet = true;
      if (turn !== 'continue') finish();
    }, 40);
    ready(finish);
    if (signal.aborted) cancel();
  });
  try {
    const wav = await done; signal.throwIfAborted();
    return quiet ? '' : await transcribe(wav, language, signal);
  } finally { ready(null); }
}

interface Recognition {
  lang: string; continuous: boolean; interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start(): void; stop(): void; abort(): void;
}
function browserListen(language: Language, signal: AbortSignal, ready: (finish: (() => void) | null) => void): Promise<string> {
  const browser = window as Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };
  const Recognition = browser.SpeechRecognition ?? browser.webkitSpeechRecognition;
  if (!Recognition) return Promise.reject(new Error('MICROPHONE_UNSUPPORTED'));
  return new Promise((resolve, reject) => {
    const recognition = new Recognition(); let text = '', settled = false;
    const cleanup = () => { clearTimeout(timer); recognition.onresult = recognition.onerror = recognition.onend = null; signal.removeEventListener('abort', cancel); ready(null); };
    const finish = (error?: unknown) => { if (settled) return; settled = true; cleanup(); try { recognition.abort(); } catch { /* Already stopped. */ } if (error) reject(error); else resolve(text); };
    const cancel = () => finish(aborted());
    const timer = setTimeout(() => finish(), 25000);
    recognition.lang = language === 'hi' || language === 'hinglish' ? 'hi-IN' : 'en-IN';
    recognition.continuous = false; recognition.interimResults = false;
    recognition.onresult = event => { text = Array.from(event.results, result => result[0]?.transcript ?? '').join(' '); };
    recognition.onerror = event => finish(event.error === 'no-speech' ? undefined : new Error('MICROPHONE_FAILED'));
    recognition.onend = () => finish();
    signal.addEventListener('abort', cancel, { once: true });
    if (signal.aborted) { cancel(); return; }
    ready(() => recognition.stop());
    try { recognition.start(); } catch (error) { finish(error); }
  });
}

export async function speakTurn(text: string, language: Language, signal: AbortSignal, provider: (name: 'sarvam' | 'browser') => void): Promise<void> {
  const config = await voiceConfig(); signal.throwIfAborted();
  const context = voicePlaybackContext();
  if (config.provider === 'sarvam' && context) {
    // A provider failure pauses the conversation, rather than listening over a missing reply.
    const audio = await synthesize(text, language, signal); signal.throwIfAborted();
    const buffer = await context.decodeAudioData(audio); signal.throwIfAborted();
    if (context.state !== 'running') throw new Error('AUDIO_BLOCKED');
    provider('sarvam');
    return new Promise((resolve, reject) => {
      const source = context.createBufferSource(); source.buffer = buffer; source.connect(context.destination);
      const cleanup = () => { source.onended = null; source.disconnect(); signal.removeEventListener('abort', cancel); };
      const cancel = () => { source.onended = null; try { source.stop(); } catch { /* Already stopped. */ } cleanup(); reject(aborted()); };
      source.onended = () => { cleanup(); resolve(); };
      signal.addEventListener('abort', cancel, { once: true });
      if (signal.aborted) { cancel(); return; }
      try { source.start(); } catch (error) { cleanup(); reject(error); }
    });
  }
  provider('browser');
  if (!window.speechSynthesis || typeof window.SpeechSynthesisUtterance !== 'function') throw new Error('AUDIO_UNSUPPORTED');
  return new Promise((resolve, reject) => {
    const speech = new SpeechSynthesisUtterance(text);
    speech.lang = language === 'hi' || language === 'hinglish' || /[\u0900-\u097f]/.test(text) ? 'hi-IN' : 'en-IN'; speech.rate = .95;
    const cleanup = () => { speech.onend = speech.onerror = null; signal.removeEventListener('abort', cancel); };
    const cancel = () => { cleanup(); window.speechSynthesis.cancel(); reject(aborted()); };
    speech.onend = () => { cleanup(); resolve(); };
    speech.onerror = () => { cleanup(); reject(new Error('AUDIO_BLOCKED')); };
    signal.addEventListener('abort', cancel, { once: true });
    if (signal.aborted) { cancel(); return; }
    window.speechSynthesis.speak(speech);
  });
}
