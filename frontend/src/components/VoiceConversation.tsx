import { useEffect, useRef, useState } from 'react';
import { Mic, Pause, PhoneOff, Play, Square, Volume2 } from 'lucide-react';
import type { Copy } from '../i18n';
import type { Language } from '../types';
import { VoiceConversation as Conversation } from '../voice/conversation';
import type { ConversationPhase, SpokenReply } from '../voice/conversation';
import { listenForTurn, speakTurn } from '../voice/conversation-audio';
import { primeVoicePlayback } from '../voice/playback';
import { registerVoiceStop, voiceConfig } from '../voice/client';

export function VoiceConversation({ copy, language, onTurn, onClose }: {
  copy: Copy; language: Language; onTurn: (text: string) => Promise<SpokenReply>; onClose: () => void;
}) {
  const [phase, setPhase] = useState<ConversationPhase>('listening');
  const [provider, setProvider] = useState<'sarvam' | 'browser' | null>(null);
  const [transcript, setTranscript] = useState<Array<{ role: 'user' | 'assistant'; text: string }>>([]);
  const session = useRef<Conversation | null>(null), finish = useRef<(() => void) | null>(null);
  const latest = useRef({ onTurn, onClose }); latest.current = { onTurn, onClose };
  const endButton = useRef<HTMLButtonElement>(null), thread = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let mounted = true;
    const previousFocus = document.activeElement as HTMLElement | null;
    const engine = new Conversation({
      listen: signal => listenForTurn(language, signal, value => { finish.current = value; if (mounted && value === null && !signal.aborted) setPhase('transcribing'); }),
      respond: text => latest.current.onTurn(text),
      speak: (text, signal) => speakTurn(text, language, signal, value => { if (mounted) setProvider(value); }),
      phase: value => { if (mounted) setPhase(value); },
      transcript: (role, text) => { if (mounted) setTranscript(previous => [...previous, { role, text }].slice(-12)); },
    });
    session.current = engine;
    void voiceConfig().then(config => { if (mounted) setProvider(config.provider); });
    const unregister = registerVoiceStop(() => { engine.stop(); latest.current.onClose(); });
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); engine.stop(); latest.current.onClose(); } };
    document.addEventListener('keydown', escape);
    endButton.current?.focus();
    // StrictMode may discard the first setup before any microphone request begins.
    queueMicrotask(() => { if (mounted) void engine.start(); });
    return () => {
      mounted = false; engine.stop(); unregister(); document.removeEventListener('keydown', escape);
      if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
    };
  }, [language]);
  useEffect(() => { thread.current?.scrollTo({ top: thread.current.scrollHeight }); }, [transcript]);
  function restart() { primeVoicePlayback(); void session.current?.start(); }
  const resting = phase === 'paused' || phase === 'error';
  const label = phase === 'listening' ? copy.voiceSessionListening : phase === 'transcribing' ? copy.voiceSessionTranscribing : phase === 'thinking' ? copy.voiceSessionThinking : phase === 'speaking' ? copy.voiceSessionSpeaking : phase === 'complete' ? copy.voiceSessionComplete : phase === 'error' ? copy.voiceSessionError : copy.voiceSessionPaused;
  return <section className="voice-session" aria-label={copy.voiceSessionTitle}>
    <header className="voice-session-head"><h2>{copy.voiceSessionTitle}</h2><button ref={endButton} type="button" className="icon-button" aria-label={copy.voiceSessionEnd} onClick={onClose}><PhoneOff size={19}/></button></header>
    <div className={`voice-session-state is-${phase}`}>
      <div className="voice-session-wave" aria-hidden="true">{[0, 1, 2, 3, 4].map(index => <span key={index}/>)}</div>
      <p role="status" aria-live="polite">{label}</p>
      <span className="small muted">{provider === 'sarvam' ? copy.voiceSarvam : provider === 'browser' ? copy.voiceBrowser : copy.voicePreparing}</span>
    </div>
    <p className="voice-session-hint">{copy.voiceSessionHint}</p>
    <div className="voice-session-transcript" ref={thread} role="log" aria-label={copy.conversation} aria-live="off">
      {transcript.length ? transcript.map((turn, index) => <div key={index} className={`voice-session-turn ${turn.role}`}><span>{turn.role === 'user' ? copy.voiceSessionYou : 'CareCompass'}</span><p>{turn.text}</p></div>) : <p className="muted">{copy.voiceSessionWelcome}</p>}
    </div>
    <div className="voice-session-controls">
      {phase === 'listening' ? <button type="button" className="button primary" onClick={() => finish.current?.()}><Square size={16}/>{copy.voiceSessionSend}</button> : null}
      {phase === 'speaking' ? <button type="button" className="button primary" onClick={restart}><Mic size={17}/>{copy.voiceSessionInterrupt}</button> : null}
      {resting ? <button type="button" className="button primary" onClick={restart}><Play size={17}/>{copy.voiceSessionResume}</button> : phase !== 'complete' ? <button type="button" className="text-button" onClick={() => session.current?.pause()} disabled={phase === 'thinking'}><Pause size={17}/>{copy.voiceSessionPause}</button> : null}
      <button type="button" className="text-button" onClick={onClose}><PhoneOff size={17}/>{phase === 'complete' ? copy.voiceSessionView : copy.voiceSessionEnd}</button>
    </div>
    <p className="small muted voice-session-foot"><Volume2 size={14}/>{copy.voiceSessionPrivacy}</p>
  </section>;
}
