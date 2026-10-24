import { useEffect, useRef, useState } from 'react';
import { Mic, Square, Volume2 } from 'lucide-react';
import type { Copy } from '../i18n';

interface SpeechResultEvent { results: { [index: number]: { [index: number]: { transcript: string } }; length: number } }
interface Recognition { lang: string; continuous: boolean; interimResults: boolean; onresult: ((event: SpeechResultEvent) => void) | null; onerror: (() => void) | null; onend: (() => void) | null; start(): void; stop(): void; abort(): void }
type SpeechWindow = Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };

export function VoiceInput({ copy, hindi, disabled, onTranscript }: { copy: Copy; hindi: boolean; disabled: boolean; onTranscript: (text: string) => void }) {
  const [listening, setListening] = useState(false);
  const [notice, setNotice] = useState('');
  const recognition = useRef<Recognition | null>(null);
  useEffect(() => () => { const current = recognition.current; if (current) { current.onend = null; current.onerror = null; current.onresult = null; current.abort(); } }, []);
  useEffect(() => { if (disabled) { recognition.current?.abort(); setListening(false); } }, [disabled]);
  function toggle() {
    if (listening) { recognition.current?.stop(); return; }
    const Speech = (window as SpeechWindow).SpeechRecognition ?? (window as SpeechWindow).webkitSpeechRecognition;
    if (!Speech) { setNotice(copy.voiceUnsupported); return; }
    const next = new Speech();
    recognition.current = next;
    next.lang = hindi ? 'hi-IN' : 'en-IN'; next.continuous = false; next.interimResults = false;
    next.onresult = event => { const text = event.results[0]?.[0]?.transcript; if (text) { onTranscript(text); setNotice(copy.voiceReview); } };
    next.onerror = () => { setNotice(copy.voiceError); setListening(false); };
    next.onend = () => setListening(false);
    try { next.start(); setListening(true); setNotice(''); } catch { setNotice(copy.voiceError); }
  }
  return <div className="voice-wrap"><button type="button" className={`voice-button ${listening ? 'is-listening' : ''}`} onClick={toggle} disabled={disabled} aria-pressed={listening}>{listening ? <Square size={16} /> : <Mic size={18} />}{listening ? copy.stop : copy.speak}</button>
    {listening ? <span role="status" className="voice-status">{copy.listening}</span> : null}
    {notice ? <p role="status" className="small voice-notice">{notice}</p> : null}
  </div>;
}
export function ReadAloud({ text, copy, hindi }: { text: string; copy: Copy; hindi: boolean }) {
  const [notice, setNotice] = useState('');
  useEffect(() => () => window.speechSynthesis?.cancel(), []);
  function read() {
    if (!('speechSynthesis' in window)) { setNotice(copy.readUnsupported); return; }
    window.speechSynthesis.cancel();
    const speech = new SpeechSynthesisUtterance(text); speech.lang = hindi ? 'hi-IN' : 'en-IN'; speech.rate = 0.9;
    window.speechSynthesis.speak(speech);
  }
  return <><button type="button" className="text-button" onClick={read}><Volume2 size={17} />{copy.readAloud}</button>{notice ? <p role="status">{notice}</p> : null}</>;
}
