import test from 'node:test';
import assert from 'node:assert/strict';
import { VoiceConversation, TurnSilence } from '../src/voice/conversation.ts';
import type { ConversationPhase, ConversationIO } from '../src/voice/conversation.ts';
import { scheduleResponseVoice, suppressResponseVoice } from '../src/voice/playback.ts';

function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; }
const tick = () => new Promise<void>(resolve => setImmediate(resolve));
function fixture(changes: Partial<ConversationIO> = {}) {
  const events: string[] = [];
  const phases: ConversationPhase[] = [];
  const io: ConversationIO = {
    listen: async () => 'a care need', respond: async () => ({ text: 'a question', terminal: true }),
    speak: async () => { events.push('speak'); },
    phase: phase => { phases.push(phase); },
    transcript: (role, text) => { events.push(`${role}:${text}`); }, ...changes,
  };
  return { session: new VoiceConversation(io), events, phases };
}

test('conversation submits a spoken turn, waits for playback, then listens again', async () => {
  const playback = deferred<void>(); let listens = 0;
  const f = fixture({ listen: async () => ++listens === 1 ? 'I need help' : '', respond: async () => ({ text: 'What kind of care?' }), speak: () => playback.promise });
  const running = f.session.start(); await tick();
  assert.equal(listens, 1); assert.deepEqual(f.phases, ['listening', 'thinking', 'speaking']);
  playback.resolve(); await running;
  assert.equal(listens, 2); assert.equal(f.phases.at(-1), 'paused');
  assert.deepEqual(f.events, ['user:I need help', 'assistant:What kind of care?']);
});

test('silence pauses without submitting, speaking, or opening another microphone', async () => {
  let requests = 0;
  const f = fixture({ listen: async () => '  ', respond: async () => { requests++; return { text: 'unexpected' }; } });
  await f.session.start(); assert.equal(requests, 0); assert.deepEqual(f.phases, ['listening', 'paused']);
});

test('ending during an API request ignores its late reply and never restarts audio', async () => {
  const response = deferred<{ text: string }>(); let spoken = 0;
  const f = fixture({ respond: () => response.promise, speak: async () => { spoken++; } });
  const running = f.session.start(); await tick(); f.session.stop(); response.resolve({ text: 'late reply' }); await running;
  assert.equal(spoken, 0); assert.deepEqual(f.events, ['user:a care need']); assert.equal(f.phases.at(-1), 'thinking');
});

test('pausing aborts microphone capture; resuming starts a fresh turn', async () => {
  let captures = 0, aborted = 0;
  const f = fixture({ listen: signal => {
    captures++;
    if (captures === 2) return Promise.resolve('resumed');
    return new Promise((_, reject) => signal.addEventListener('abort', () => { aborted++; reject(new Error('aborted')); }));
  } });
  const running = f.session.start(); await tick(); f.session.pause(); await running;
  assert.equal(aborted, 1); assert.equal(f.phases.at(-1), 'paused');
  await f.session.start(); assert.equal(captures, 2); assert.equal(f.phases.at(-1), 'complete');
});

test('Speak now aborts playback before opening the next microphone', async () => {
  const order: string[] = []; let listens = 0;
  const f = fixture({ listen: async () => { order.push('listen'); return ++listens === 1 ? 'request' : ''; },
    respond: async () => ({ text: 'reply' }), speak: (_, signal) => new Promise((_, reject) => signal.addEventListener('abort', () => { order.push('stop speaker'); reject(new Error('interrupted')); })) });
  const running = f.session.start(); await tick(); await f.session.start(); await running;
  assert.deepEqual(order, ['listen', 'stop speaker', 'listen']);
});

test('emergency reply ends the loop without another listen or automatic booking action', async () => {
  let listens = 0;
  const f = fixture({ listen: async () => { listens++; return 'request'; }, respond: async () => ({ text: 'emergency guidance', terminal: true }) });
  await f.session.start(); assert.equal(listens, 1); assert.equal(f.phases.at(-1), 'complete');
});

test('provider failure pauses the loop rather than listening over an unheard reply', async () => {
  const f = fixture({ speak: async () => { throw new Error('provider unavailable'); } });
  await f.session.start(); assert.equal(f.phases.at(-1), 'error'); assert.equal(f.phases.filter(p => p === 'listening').length, 1);
});

test('turn detection waits through short hesitations, finishes after speech, and times out silence', () => {
  const detector = new TurnSilence();
  assert.equal(detector.sample(0, 4000), 'continue');
  assert.equal(detector.sample(.03, 4100), 'continue'); assert.equal(detector.sample(.04, 4200), 'continue');
  assert.equal(detector.sample(0, 4800), 'continue'); assert.equal(detector.sample(.05, 4900), 'continue');
  assert.equal(detector.sample(0, 6200), 'finish');
  assert.equal(new TurnSilence().sample(0, 10001), 'quiet');
  const noise = new TurnSilence(); noise.sample(.03, 1000);
  assert.equal(noise.sample(0, 10001), 'quiet');
});

test('a session-owned late response cannot start standalone automatic read-aloud after End', async () => {
  const response = {}; let spoken = 0;
  suppressResponseVoice(response); scheduleResponseVoice(response, () => { spoken++; }); await Promise.resolve();
  assert.equal(spoken, 0);
});
