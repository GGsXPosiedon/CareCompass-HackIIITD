import type { Language } from '../types';
import { encodeWav, RECORDING_SECONDS } from './wav.ts';
import { spokenLanguage } from './locale.ts';

export interface VoiceConfig { provider: 'sarvam' | 'browser'; maxSeconds: number }
let config: Promise<VoiceConfig> | undefined;
export function voiceConfig(): Promise<VoiceConfig> {
  return config ??= fetch('/api/voice', { signal: AbortSignal.timeout(4000) })
    .then(async response => {
      if (!response.ok) throw new Error('VOICE_CONFIG_UNAVAILABLE');
      const value = await response.json();
      return { provider: value.provider === 'sarvam' ? 'sarvam' : 'browser', maxSeconds: RECORDING_SECONDS } as VoiceConfig;
    }).catch(() => { config = undefined; return { provider: 'browser', maxSeconds: RECORDING_SECONDS }; });
}

export class VoiceError extends Error {
  readonly status: number;
  constructor(status: number) { super('VOICE_REQUEST_FAILED'); this.status = status; }
}
export async function transcribe(wav: Blob, language: Language, signal: AbortSignal): Promise<string> {
  const response = await fetch(`/api/voice?action=transcribe&language=${language}`, {
    method: 'POST', headers: { 'Content-Type': 'audio/wav', 'X-CareCompass-Voice': '1' }, body: wav,
    signal: AbortSignal.any([signal, AbortSignal.timeout(30000)]),
  });
  if (!response.ok) throw new VoiceError(response.status);
  const result = await response.json();
  if (typeof result.text !== 'string') throw new VoiceError(502);
  return result.text;
}
export async function synthesize(text: string, language: Language, signal: AbortSignal): Promise<ArrayBuffer> {
  language = spokenLanguage(language, text);
  const response = await fetch(`/api/voice?action=speak&language=${language}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CareCompass-Voice': '1' }, body: JSON.stringify({ text }),
    signal: AbortSignal.any([signal, AbortSignal.timeout(30000)]),
  });
  if (!response.ok) throw new VoiceError(response.status);
  if (!response.headers.get('content-type')?.startsWith('audio/')) throw new VoiceError(502);
  return response.arrayBuffer();
}
const stops = new Set<() => void>();
export function registerVoiceStop(stop: () => void) { stops.add(stop); return () => { stops.delete(stop); }; }
export function stopAllVoice() { stops.forEach(stop => stop()); }

export interface Recording { stop: () => Promise<Blob>; cancel: () => void }
export function supportsRecording() {
  return window.isSecureContext && typeof navigator.mediaDevices?.getUserMedia === 'function' && typeof window.MediaRecorder === 'function' && typeof window.AudioContext === 'function';
}
export function recordStream(stream: MediaStream, onLimit: () => void): Recording {
  const mimeType = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm', 'audio/ogg;codecs=opus'].find(type => MediaRecorder.isTypeSupported(type));
  let recorder: MediaRecorder;
  try { recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined); }
  catch (error) { stream.getTracks().forEach(track => track.stop()); throw error; }
  const chunks: Blob[] = [];
  let canceled = false, finished: Promise<Blob> | undefined;
  const raw = new Promise<Blob>((resolve, reject) => {
    recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    recorder.onerror = () => { release(); reject(new Error('RECORDING_FAILED')); onLimit(); };
    recorder.onstop = () => resolve(new Blob(chunks, { type: recorder.mimeType }));
  });
  void raw.catch(() => {});
  let timer: ReturnType<typeof setTimeout>;
  const release = () => { clearTimeout(timer); stream.getTracks().forEach(track => track.stop()); };
  try { recorder.start(); timer = setTimeout(onLimit, RECORDING_SECONDS * 1000); }
  catch (error) { release(); throw error; }
  return {
    stop: () => finished ??= (async () => {
      if (recorder.state !== 'inactive') recorder.stop();
      release();
      const blob = await raw;
      if (canceled || !blob.size) throw new Error('RECORDING_CANCELED');
      const context = new AudioContext();
      try {
        const decoded = await context.decodeAudioData(await blob.arrayBuffer());
        const mono = new Float32Array(decoded.length);
        for (let channel = 0; channel < decoded.numberOfChannels; channel++) {
          const samples = decoded.getChannelData(channel);
          for (let i = 0; i < mono.length; i++) mono[i] += samples[i] / decoded.numberOfChannels;
        }
        if (canceled) throw new Error('RECORDING_CANCELED');
        return new Blob([encodeWav(mono, decoded.sampleRate)], { type: 'audio/wav' });
      } finally { await context.close(); }
    })(),
    cancel: () => { canceled = true; if (recorder.state !== 'inactive') recorder.stop(); release(); },
  };
}
