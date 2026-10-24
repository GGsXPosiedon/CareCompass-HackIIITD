export type ConversationPhase = 'listening' | 'transcribing' | 'thinking' | 'speaking' | 'paused' | 'error' | 'complete';
export interface SpokenReply { text: string; terminal?: boolean }
export interface ConversationIO {
  listen(signal: AbortSignal): Promise<string>;
  respond(text: string, signal: AbortSignal): Promise<SpokenReply>;
  speak(text: string, signal: AbortSignal): Promise<void>;
  phase(phase: ConversationPhase): void;
  transcript(role: 'user' | 'assistant', text: string): void;
}
// One microphone or speaker at a time; cancellation invalidates even non-abortable API replies.
export class VoiceConversation {
  private controller: AbortController | null = null;
  private generation = 0;
  private io: ConversationIO;
  constructor(io: ConversationIO) { this.io = io; }
  pause() { this.generation++; this.controller?.abort(); this.controller = null; this.io.phase('paused'); }
  stop() { this.generation++; this.controller?.abort(); this.controller = null; }
  async start() {
    this.stop();
    const generation = this.generation;
    const controller = new AbortController(); this.controller = controller;
    const current = () => !controller.signal.aborted && generation === this.generation;
    try {
      while (current()) {
        this.io.phase('listening');
        const text = (await this.io.listen(controller.signal)).trim();
        if (!current()) return;
        if (!text) { this.io.phase('paused'); return; }
        this.io.transcript('user', text); this.io.phase('thinking');
        const reply = await this.io.respond(text, controller.signal);
        if (!current()) return;
        if (!reply.text.trim()) throw new Error('EMPTY_REPLY');
        this.io.transcript('assistant', reply.text); this.io.phase('speaking');
        await this.io.speak(reply.text, controller.signal);
        if (!current()) return;
        if (reply.terminal) { this.io.phase('complete'); return; }
      }
    } catch { if (current()) this.io.phase('error'); }
    finally { if (generation === this.generation) this.controller = null; }
  }
}

// Require real speech before a pause can complete a turn. Silence alone never sends a request.
export class TurnSilence {
  private voiced = 0;
  private lastVoice = 0;
  sample(rms: number, elapsed: number): 'continue' | 'finish' | 'quiet' {
    if (rms >= .018) { this.voiced++; this.lastVoice = elapsed; }
    if (this.voiced >= 2 && elapsed - this.lastVoice >= 1250) return 'finish';
    if (this.voiced < 2 && elapsed >= 10000) return 'quiet';
    return 'continue';
  }
}
