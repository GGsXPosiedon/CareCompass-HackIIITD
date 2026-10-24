import test from 'node:test';
import assert from 'node:assert/strict';
import { listenForTurn, speakTurn } from '../src/voice/conversation-audio.ts';

// Browser adapters are exercised without using the real microphone or a paid provider.
test('browser capture returns final words, uses the selected language, and releases handlers', async () => {
  const originalWindow = Object.getOwnPropertyDescriptor(globalThis, 'window'), originalFetch = globalThis.fetch;
  let recognition!: FakeRecognition, aborts = 0;
  class FakeRecognition {
    lang = ''; continuous = false; interimResults = false;
    onresult: ((event: { results: Array<Array<{ transcript: string }>> }) => void) | null = null;
    onerror: ((event: { error?: string }) => void) | null = null;
    onend: (() => void) | null = null;
    constructor() { recognition = this; }
    start() { queueMicrotask(() => { this.onresult?.({ results: [[{ transcript: 'a spoken answer' }]] }); this.onend?.(); }); }
    stop() { this.onend?.(); }
    abort() { aborts++; }
  }
  Object.defineProperty(globalThis, 'window', { configurable: true, value: { SpeechRecognition: FakeRecognition } });
  globalThis.fetch = async () => Response.json({ provider: 'browser' });
  const ready: unknown[] = [];
  try {
    const text = await listenForTurn('hinglish', new AbortController().signal, finish => ready.push(finish));
    assert.equal(text, 'a spoken answer'); assert.equal(recognition.lang, 'hi-IN');
    assert.equal(aborts, 1); assert.equal(recognition.onresult, null); assert.equal(recognition.onend, null);
    assert.equal(typeof ready[0], 'function'); assert.equal(ready.at(-1), null);
  } finally { globalThis.fetch = originalFetch; if (originalWindow) Object.defineProperty(globalThis, 'window', originalWindow); else Reflect.deleteProperty(globalThis, 'window'); }
});

test('ending a browser capture aborts recognition and rejects the pending turn', async () => {
  const original = Object.getOwnPropertyDescriptor(globalThis, 'window'); let aborted = false;
  class Recognition {
    start() {} stop() {} abort() { aborted = true; }
  }
  Object.defineProperty(globalThis, 'window', { configurable: true, value: { SpeechRecognition: Recognition } });
  const controller = new AbortController();
  try {
    let started!: () => void; const ready = new Promise<void>(resolve => { started = resolve; });
    const turn = listenForTurn('en', controller.signal, finish => { if (finish) started(); });
    await ready; controller.abort();
    await assert.rejects(turn, { name: 'AbortError' }); assert.equal(aborted, true);
  } finally { if (original) Object.defineProperty(globalThis, 'window', original); else Reflect.deleteProperty(globalThis, 'window'); }
});

test('interrupting browser speech cancels audio and removes its completion callbacks', async () => {
  const originalWindow = Object.getOwnPropertyDescriptor(globalThis, 'window');
  const originalSpeech = Object.getOwnPropertyDescriptor(globalThis, 'SpeechSynthesisUtterance');
  let spoken!: Speech, cancelled = 0, began!: () => void;
  const started = new Promise<void>(resolve => { began = resolve; });
  class Speech {
    text: string; lang = ''; rate = 1; onend: (() => void) | null = null; onerror: (() => void) | null = null;
    constructor(text: string) { this.text = text; }
  }
  Object.defineProperty(globalThis, 'SpeechSynthesisUtterance', { configurable: true, value: Speech });
  Object.defineProperty(globalThis, 'window', { configurable: true, value: { SpeechSynthesisUtterance: Speech,
    speechSynthesis: { speak: (speech: Speech) => { spoken = speech; began(); }, cancel: () => { cancelled++; } } } });
  const controller = new AbortController();
  try {
    const playing = speakTurn('A reply', 'en', controller.signal, () => {});
    await started; controller.abort(); await assert.rejects(playing, { name: 'AbortError' });
    assert.equal(cancelled, 1); assert.equal(spoken.onend, null); assert.equal(spoken.onerror, null);
  } finally {
    if (originalWindow) Object.defineProperty(globalThis, 'window', originalWindow); else Reflect.deleteProperty(globalThis, 'window');
    if (originalSpeech) Object.defineProperty(globalThis, 'SpeechSynthesisUtterance', originalSpeech); else Reflect.deleteProperty(globalThis, 'SpeechSynthesisUtterance');
  }
});
