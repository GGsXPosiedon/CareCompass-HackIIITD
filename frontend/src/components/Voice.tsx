import { useContext, useEffect, useRef, useState } from 'react';
import { Mic, Square, Volume2 } from 'lucide-react';
import type { Copy } from '../i18n';
import { VoiceLanguageContext } from '../voice/language';
import { recordStream, registerVoiceStop, stopAllVoice, supportsRecording, synthesize, transcribe, voiceConfig } from '../voice/client';
import type { Recording, VoiceConfig } from '../voice/client';

interface Recognition {
  lang: string; continuous: boolean; interimResults: boolean;
  onresult: ((event: { results: { [index: number]: { [index: number]: { transcript: string } } } }) => void) | null;
  onerror: (() => void) | null; onend: (() => void) | null;
  start(): void; stop(): void; abort(): void;
}
type SpeechWindow = Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };

export function VoiceInput({ copy, hindi, disabled, onTranscript }: { copy: Copy; hindi: boolean; disabled: boolean; onTranscript: (text: string) => void }) {
  const selectedLanguage = useContext(VoiceLanguageContext);
  const language = hindi ? 'hi' : selectedLanguage;
  const [phase, setPhase] = useState<'idle' | 'permission' | 'recording' | 'transcribing'>('idle');
  const [notice, setNotice] = useState('');
  const [provider, setProvider] = useState<VoiceConfig['provider'] | null>(null);
  const recording = useRef<Recording | null>(null), recognition = useRef<Recognition | null>(null);
  const request = useRef<AbortController | null>(null), generation = useRef(0), mounted = useRef(false);
  const fallbackTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const transcriptCallback = useRef(onTranscript); transcriptCallback.current = onTranscript;

  function cancel() {
    generation.current++; request.current?.abort(); request.current = null;
    recording.current?.cancel(); recording.current = null; clearTimeout(fallbackTimer.current);
    const old = recognition.current; recognition.current = null;
    if (old) { old.onresult = old.onerror = old.onend = null; try { old.abort(); } catch { /* Already stopped. */ } }
    if (mounted.current) setPhase('idle');
  }
  useEffect(() => {
    mounted.current = true;
    void voiceConfig().then(value => { if (mounted.current) setProvider(value.provider); });
    const unregister = registerVoiceStop(cancel);
    return () => { mounted.current = false; cancel(); unregister(); };
  }, []);
  useEffect(() => { cancel(); }, [disabled, language]);

  async function finish() {
    const active = recording.current;
    if (!active) { recognition.current?.stop(); return; }
    recording.current = null;
    const id = generation.current;
    setPhase('transcribing');
    const controller = new AbortController(); request.current = controller;
    try {
      const wav = await active.stop();
      if (id !== generation.current) return;
      const text = await transcribe(wav, language, controller.signal);
      if (id !== generation.current) return;
      if (text) transcriptCallback.current(text);
      setNotice(text ? copy.voiceReview : copy.voiceNoSpeech);
    } catch { if (id === generation.current) setNotice(copy.voiceError); }
    finally { if (id === generation.current) { request.current = null; setPhase('idle'); } }
  }
  async function toggle() {
    if (phase === 'recording') { void finish(); return; }
    if (phase !== 'idle') { cancel(); return; }
    stopAllVoice(); setNotice('');
    const id = ++generation.current; setPhase('permission');
    try {
      const config = await voiceConfig();
      if (id !== generation.current) return;
      setProvider(config.provider);
      if (config.provider === 'sarvam') {
        if (!supportsRecording()) { setNotice(copy.voiceUnsupported); setPhase('idle'); return; }
        const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
        if (id !== generation.current) { stream.getTracks().forEach(track => track.stop()); return; }
        recording.current = recordStream(stream, () => { void finish(); }); setPhase('recording');
      } else {
        const Speech = (window as SpeechWindow).SpeechRecognition ?? (window as SpeechWindow).webkitSpeechRecognition;
        if (!Speech) { setNotice(copy.voiceUnsupported); setPhase('idle'); return; }
        const next = new Speech(); recognition.current = next;
        next.lang = language === 'hi' || language === 'hinglish' ? 'hi-IN' : 'en-IN';
        next.continuous = false; next.interimResults = false;
        next.onresult = event => {
          if (id !== generation.current) return;
          const text = event.results[0]?.[0]?.transcript;
          if (text) { transcriptCallback.current(text); setNotice(copy.voiceReview); }
        };
        next.onerror = () => { if (id === generation.current) { setNotice(copy.voiceError); setPhase('idle'); } };
        next.onend = () => { if (id === generation.current) { clearTimeout(fallbackTimer.current); setPhase('idle'); } };
        next.start(); setPhase('recording'); fallbackTimer.current = setTimeout(() => next.stop(), 25000);
      }
    } catch { if (id === generation.current) { cancel(); setNotice(copy.voiceError); } }
  }
  const label = phase === 'permission' ? copy.voicePermission : phase === 'transcribing' ? copy.voiceTranscribing : phase === 'recording' ? copy.stop : copy.speak;
  return <div className="voice-wrap">
    <button type="button" className={`voice-button ${phase === 'recording' ? 'is-listening' : ''}`} onClick={() => void toggle()} disabled={disabled} aria-pressed={phase !== 'idle'} aria-label={label} title={provider === 'sarvam' ? copy.voiceSarvam : copy.voiceBrowser}>
      {phase === 'idle' ? <Mic size={18}/> : <Square size={16}/>}<span>{label}</span>
    </button>
    {phase === 'recording' ? <span role="status" className="voice-status">{copy.listening}</span> : null}
    {notice || phase === 'transcribing' ? <p role="status" className="small voice-notice">{notice || copy.voiceTranscribing}{provider === 'browser' ? ` ${copy.voiceBrowser}` : ''}</p> : null}
  </div>;
}

export function ReadAloud({ text, copy, hindi }: { text: string; copy: Copy; hindi: boolean }) {
  const selectedLanguage = useContext(VoiceLanguageContext);
  const language = hindi ? 'hi' : selectedLanguage;
  const [phase, setPhase] = useState<'idle' | 'loading' | 'playing'>('idle');
  const [notice, setNotice] = useState('');
  const request = useRef<AbortController | null>(null), generation = useRef(0), mounted = useRef(false);
  const context = useRef<AudioContext | null>(null), source = useRef<AudioBufferSourceNode | null>(null);
  const utterance = useRef<SpeechSynthesisUtterance | null>(null);
  function cancel() {
    generation.current++; request.current?.abort(); request.current = null;
    if (source.current) { source.current.onended = null; try { source.current.stop(); } catch { /* Already ended. */ } source.current = null; }
    if (context.current) { void context.current.close().catch(() => {}); context.current = null; }
    if (utterance.current) { utterance.current.onend = utterance.current.onerror = null; window.speechSynthesis?.cancel(); utterance.current = null; }
    if (mounted.current) setPhase('idle');
  }
  useEffect(() => {
    mounted.current = true; const unregister = registerVoiceStop(cancel);
    return () => { mounted.current = false; cancel(); unregister(); };
  }, []);
  useEffect(() => { cancel(); setNotice(''); }, [text, language]);
  function browserVoice(id: number, fallback = false) {
    if (!('speechSynthesis' in window) || typeof window.SpeechSynthesisUtterance !== 'function') { setNotice(copy.readUnsupported); setPhase('idle'); return; }
    const speech = new SpeechSynthesisUtterance(text); utterance.current = speech;
    speech.lang = language === 'hi' || language === 'hinglish' || /[\u0900-\u097f]/.test(text) ? 'hi-IN' : 'en-IN'; speech.rate = .95;
    speech.onend = () => { if (id === generation.current) { utterance.current = null; setPhase('idle'); } };
    speech.onerror = () => { if (id === generation.current) { setPhase('idle'); setNotice(copy.readUnsupported); } };
    setNotice(fallback ? copy.voiceFallback : copy.voiceBrowserShort); setPhase('playing'); window.speechSynthesis.speak(speech);
  }
  async function read() {
    if (phase !== 'idle') { cancel(); return; }
    stopAllVoice(); setNotice('');
    const id = ++generation.current; setPhase('loading');
    // Resume within the user's gesture, before fetching audio (including iOS).
    let audioContext: AudioContext | null = null;
    try {
      audioContext = window.AudioContext ? new AudioContext() : null; context.current = audioContext;
      const resumed = audioContext?.resume().catch(() => {});
      const config = await voiceConfig();
      if (id !== generation.current) return;
      if (config.provider !== 'sarvam' || !audioContext) {
        if (audioContext) { await audioContext.close(); context.current = null; }
        browserVoice(id); return;
      }
      const controller = new AbortController(); request.current = controller;
      const audio = await synthesize(text, language, controller.signal);
      if (id !== generation.current) return;
      const buffer = await audioContext.decodeAudioData(audio); await resumed;
      if (id !== generation.current) return;
      if (audioContext.state !== 'running') throw new Error('PLAYBACK_BLOCKED');
      const player = audioContext.createBufferSource(); player.buffer = buffer; player.connect(audioContext.destination);
      source.current = player; player.onended = () => { if (id === generation.current) cancel(); };
      player.start(); setNotice(copy.voiceSarvam); setPhase('playing');
    } catch {
      if (id !== generation.current) return;
      if (audioContext && audioContext.state !== 'closed') await audioContext.close().catch(() => {});
      context.current = null; browserVoice(id, true);
    }
  }
  return <span className="read-aloud"><button type="button" className="text-button" onClick={() => void read()} aria-pressed={phase !== 'idle'}>
    {phase === 'idle' ? <Volume2 size={17}/> : <Square size={17}/>} {phase === 'loading' ? copy.voicePreparing : phase === 'playing' ? copy.voiceStopPlayback : copy.readAloud}
  </button>{notice ? <span role="status" className="small muted voice-output-notice">{notice}</span> : null}</span>;
}
