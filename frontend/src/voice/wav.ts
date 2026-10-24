export const RECORDING_SECONDS = 25;
export const VOICE_SAMPLE_RATE = 16000;

/** Mono PCM16 WAV, matching GD Arena's Sarvam upload format. */
export function encodeWav(samples: Float32Array, sourceRate: number): ArrayBuffer {
  if (!Number.isFinite(sourceRate) || sourceRate <= 0) throw new Error('INVALID_SAMPLE_RATE');
  const length = Math.floor(samples.length * VOICE_SAMPLE_RATE / sourceRate);
  const buffer = new ArrayBuffer(44 + length * 2);
  const view = new DataView(buffer);
  const tag = (offset: number, text: string) => [...text].forEach((char, i) => view.setUint8(offset + i, char.charCodeAt(0)));
  tag(0, 'RIFF'); view.setUint32(4, 36 + length * 2, true); tag(8, 'WAVE');
  tag(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, VOICE_SAMPLE_RATE, true);
  view.setUint32(28, VOICE_SAMPLE_RATE * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  tag(36, 'data'); view.setUint32(40, length * 2, true);
  const ratio = sourceRate / VOICE_SAMPLE_RATE;
  for (let i = 0; i < length; i++) {
    const start = Math.floor(i * ratio), end = Math.min(samples.length, Math.max(start + 1, Math.floor((i + 1) * ratio)));
    let value = 0;
    for (let j = start; j < end; j++) value += samples[j];
    value = Math.max(-1, Math.min(1, value / (end - start)));
    view.setInt16(44 + i * 2, Math.round(value * (value < 0 ? 32768 : 32767)), true);
  }
  return buffer;
}

export function inspectWav(bytes: Uint8Array): { seconds: number; silent: boolean } {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const tag = (offset: number) => String.fromCharCode(...bytes.slice(offset, offset + 4));
  if (bytes.length < 46 || tag(0) !== 'RIFF' || tag(8) !== 'WAVE' || tag(12) !== 'fmt ' || tag(36) !== 'data'
    || view.getUint32(16, true) !== 16 || view.getUint16(20, true) !== 1 || view.getUint16(22, true) !== 1
    || view.getUint32(24, true) !== VOICE_SAMPLE_RATE || view.getUint16(34, true) !== 16
    || view.getUint32(40, true) !== bytes.length - 44 || (bytes.length - 44) % 2) throw new Error('INVALID_WAV');
  const count = (bytes.length - 44) / 2;
  let sum = 0, peak = 0;
  for (let i = 0; i < count; i++) {
    const value = view.getInt16(44 + i * 2, true) / 32768;
    sum += value * value; peak = Math.max(peak, Math.abs(value));
  }
  return { seconds: count / VOICE_SAMPLE_RATE, silent: Math.sqrt(sum / count) < .0035 && peak < .02 };
}
