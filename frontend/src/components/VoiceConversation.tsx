import { useEffect, useRef, useState } from 'react';
import { Mic, Pause, PhoneOff, Play, Square } from 'lucide-react';
import { createPortal } from 'react-dom';
import type { Copy } from '../i18n';
import type { Language } from '../types';
import { VoiceConversation as Conversation } from '../voice/conversation';
import type { ConversationPhase, SpokenReply } from '../voice/conversation';
import { listenForTurn, speakTurn } from '../voice/conversation-audio';
import { primeVoicePlayback } from '../voice/playback';
import { registerVoiceStop, voiceConfig } from '../voice/client';

export function VoiceConversation({ copy, language, host, onTurn, onClose }: {
  copy: Copy; language: Language; host: HTMLElement | null; onTurn: (text: string, signal: AbortSignal) => Promise<SpokenReply>; onClose: () => void;
}) {
  const [phase, setPhase] = useState<ConversationPhase>('listening');
  const [provider, setProvider] = useState<'sarvam' | 'browser' | null>(null);
  const [spokenText, setSpokenText] = useState('');
  const session = useRef<Conversation | null>(null), finish = useRef<(() => void) | null>(null);
  const latest = useRef({ onTurn, onClose }); latest.current = { onTurn, onClose };
  const endButton = useRef<HTMLButtonElement>(null), focused = useRef(false);
  useEffect(() => {
    let mounted = true;
    const previousFocus = document.activeElement as HTMLElement | null;
    const engine = new Conversation({
      listen: signal => listenForTurn(language, signal, value => { finish.current = value; if (mounted && value === null && !signal.aborted) setPhase('transcribing'); }),
      respond: (text, signal) => latest.current.onTurn(text, signal),
      speak: (text, signal) => speakTurn(text, language, signal, value => { if (mounted) setProvider(value); }),
      phase: value => { if (mounted) { setPhase(value); if (value === 'listening') setSpokenText(''); } },
      transcript: (role, text) => { if (mounted && role === 'user') setSpokenText(text); },
    });
    session.current = engine;
    void voiceConfig().then(config => { if (mounted) setProvider(config.provider); });
    const unregister = registerVoiceStop(() => { engine.stop(); latest.current.onClose(); });
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); engine.stop(); latest.current.onClose(); } };
    document.addEventListener('keydown', escape);
    // StrictMode may discard the first setup before any microphone request begins.
    queueMicrotask(() => { if (mounted) void engine.start(); });
    return () => {
      mounted = false; engine.stop(); unregister(); document.removeEventListener('keydown', escape);
      if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
    };
  }, [language]);
  useEffect(() => {
    if (host && !focused.current && endButton.current) { endButton.current.focus({ preventScroll: true }); focused.current = true; }
  }, [host]);
  function restart() { primeVoicePlayback(); void session.current?.start(); }
  const resting = phase === 'paused' || phase === 'error';
  const label = phase === 'listening' ? copy.voiceSessionListening : phase === 'transcribing' ? copy.voiceSessionTranscribing : phase === 'thinking' ? copy.voiceSessionThinking : phase === 'speaking' ? copy.voiceSessionSpeaking : phase === 'complete' ? copy.voiceSessionComplete : phase === 'error' ? copy.voiceSessionError : copy.voiceSessionPaused;
  if (!host) return null;
  return createPortal(<section className={`voice-inline is-${phase}`} aria-label={copy.voiceSessionTitle}>
    <div className="voice-inline-status">
      <div className="voice-session-wave" aria-hidden="true">{[0, 1, 2, 3, 4].map(index => <span key={index}/>)}</div>
      <p role="status" aria-live="polite">{label}</p>
      <button ref={endButton} type="button" className="icon-button" aria-label={copy.voiceSessionEnd} title={copy.voiceSessionEnd} onClick={onClose}><PhoneOff size={18}/></button>
    </div>
    <p className="voice-inline-transcript" aria-label={copy.voiceSessionTranscript}>{spokenText || copy.voiceSessionWelcome}</p>
    <div className="voice-inline-actions">
      <span className="small muted">{provider === 'sarvam' ? copy.voiceSarvam : provider === 'browser' ? copy.voiceBrowserShort : copy.voicePreparing}</span>
      <div>
        {phase === 'listening' ? <button type="button" className="text-button" onClick={() => finish.current?.()}><Square size={15}/>{copy.voiceSessionSend}</button> : null}
        {phase === 'speaking' ? <button type="button" className="text-button" onClick={restart}><Mic size={16}/>{copy.voiceSessionInterrupt}</button> : null}
        {resting ? <button type="button" className="text-button" onClick={restart}><Play size={16}/>{copy.voiceSessionResume}</button> : phase !== 'complete' ? <button type="button" className="icon-button" aria-label={copy.voiceSessionPause} title={copy.voiceSessionPause} onClick={() => session.current?.pause()} disabled={phase === 'thinking'}><Pause size={17}/></button> : <button type="button" className="text-button" onClick={onClose}>{copy.voiceSessionView}</button>}
      </div>
    </div>
  </section>, host);
}
