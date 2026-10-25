import { memo, useContext, useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowRight, ArrowUp, Check, Copy as CopyIcon, MapPin, RotateCcw, Square } from 'lucide-react';
import type { Copy } from '../i18n';
import { careLabel, urgencyLabel } from '../i18n';
import type { Message, TriageResponse } from '../types';
import { isNearBottom } from '../lib/chat-scroll';
import { VoiceSessionActiveContext } from '../voice/language';
import { VoiceComposerSlot } from './VoiceComposerSlot';
import { ReadAloud, VoiceInput } from './Voice';
import { CareForChip } from './CareFor';
import { AskCard } from './ChatQuestion';

export function CareChat({ copy, hindi, messages, result, pendingText, input, setInput, onSend, onContinue, onLocation, onStop, onRetry, onEdit, busy, error }: {
  copy: Copy; hindi: boolean; messages: Message[]; result: TriageResponse | null; pendingText: string | null; input: string;
  setInput: (value: string) => void; onSend: (text: string) => void; onContinue: () => void;
  onLocation: () => void; onStop: () => void; onRetry: () => void; onEdit: () => void; busy: boolean; error: string;
}) {
  const voiceActive = useContext(VoiceSessionActiveContext);
  const viewport = useRef<HTMLDivElement>(null), content = useRef<HTMLDivElement>(null), textarea = useRef<HTMLTextAreaElement>(null);
  const following = useRef(true), frame = useRef(0);
  const [showJump, setShowJump] = useState(false);
  const initialCount = useRef(messages.length);
  const inputId = useId();
  const t = (en: string, hi: string) => hindi ? hi : en;
  function followLatest() {
    following.current = true; setShowJump(false);
    viewport.current?.scrollTo({ top: viewport.current.scrollHeight, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
  }
  // Pin the scroll viewport, not the document. Coalesce layout changes into one update per frame.
  useLayoutEffect(() => {
    const scroll = viewport.current, body = content.current;
    if (!scroll || !body) return;
    scroll.scrollTop = scroll.scrollHeight;
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(() => { if (following.current) scroll.scrollTop = scroll.scrollHeight; });
    });
    observer.observe(body); observer.observe(scroll);
    return () => { observer.disconnect(); cancelAnimationFrame(frame.current); };
  }, []);
  useLayoutEffect(() => {
    if (pendingText && busy) { following.current = true; setShowJump(false); }
    if (following.current && viewport.current) viewport.current.scrollTop = viewport.current.scrollHeight;
  }, [messages, pendingText, busy]);
  useLayoutEffect(() => {
    if (!textarea.current) return;
    textarea.current.style.height = 'auto';
    textarea.current.style.height = `${Math.min(textarea.current.scrollHeight, 180)}px`;
  }, [input, voiceActive]);
  useEffect(() => { if (!voiceActive) textarea.current?.focus({ preventScroll: true }); }, [voiceActive]);
  const latestReply = messages.at(-1)?.role === 'assistant' && !pendingText;
  // An open follow-up question is answered in the numbered card, so the question is not repeated in the thread.
  const asking = !pendingText && !!result?.follow_up_question && messages.at(-1)?.role === 'assistant';
  const shown = asking ? messages.slice(0, -1) : messages;
  return <section className="care-conversation" aria-label={copy.conversation}>
    <div ref={viewport} className="care-chat-scroll" role="region" aria-label={t('Conversation messages', 'बातचीत के संदेश')} tabIndex={0}
      onScroll={() => { if (!viewport.current) return; const near = isNearBottom(viewport.current); following.current = near; setShowJump(!near); }}>
      <div ref={content} className="care-chat-content">
        <ol className="chat-thread" role="log" aria-label={copy.conversation} aria-live="polite" aria-relevant="additions" aria-busy={busy}>
          {shown.map((message, index) => <ChatMessage key={index} message={message} copy={copy} hindi={hindi} animate={index >= initialCount.current} latest={!!latestReply && !asking && index === messages.length - 1}/>)}
          {pendingText ? <li className="chat-bubble user pending-message"><span className="chat-bubble-from">{t('You', 'आप')}</span><p>{pendingText}</p></li> : null}
        </ol>
        {busy ? <div className="care-chat-thinking" role="status"><span className="care-thinking-mark" aria-hidden="true"><i/><i/><i/></span><span>{t('Thinking', 'सोच रहे हैं')}<span className="thinking-ellipsis" aria-hidden="true">…</span></span></div> : null}
        {!pendingText && result?.service_notice ? <p className="care-service-notice" role="status">{result.service_notice}</p> : null}
        {!pendingText && result && !result.follow_up_question && result.care_type && result.urgency ? <div className="care-chat-next">
          <div><strong>{careLabel(result.care_type, hindi)}</strong><span>{urgencyLabel(result.urgency, hindi)}</span></div>
          {result.matched_caregivers.length ? <button className="button primary" disabled={busy} onClick={onContinue}>{copy.viewCaregivers}<ArrowRight size={17}/></button>
            : <button className="text-button" disabled={busy} onClick={onLocation}><MapPin size={16}/>{copy.changeArea}</button>}
        </div> : null}
        {error ? <div className="care-chat-error" role="alert"><p>{error}</p>{pendingText ? <button type="button" className="text-button" onClick={onRetry} disabled={busy}><RotateCcw size={15}/>{t('Retry response', 'फिर कोशिश करें')}</button> : null}</div> : null}
      </div>
    </div>
    {asking ? <div className="care-chat-reply care-ask-wrap">
      {showJump ? <button className="care-jump-latest" type="button" onClick={followLatest} aria-label={t('Scroll to latest message', 'नए संदेश पर जाएँ')}><ArrowDown size={18}/></button> : null}
      <AskCard key={result?.follow_up_question ?? ''} copy={copy} hindi={hindi} question={result?.follow_up_question ?? ''} answerOptions={result?.answer_options ?? []} asked={messages.filter(m => m.role === 'assistant').length}
        input={input} setInput={setInput} onAnswer={onSend} onBack={onEdit} busy={busy} error={error}/>
    </div> : <form className="care-chat-reply" onSubmit={event => { event.preventDefault(); if (input.trim() && !busy) onSend(input.trim()); }}>
      {showJump ? <button className="care-jump-latest" type="button" onClick={followLatest} aria-label={t('Scroll to latest message', 'नए संदेश पर जाएँ')}><ArrowDown size={18}/></button> : null}
      {!pendingText && result?.follow_up_question && result.answer_options?.length && !voiceActive ? <div className="care-chat-options" aria-label={t('Suggested replies', 'सुझाए गए जवाब')}>{result.answer_options.map(option => <button type="button" key={option} disabled={busy} onClick={() => onSend(option)}>{option}</button>)}</div> : null}
      <div className="care-chat-composer">{voiceActive ? <VoiceComposerSlot/> : <>
        <label className="sr-only" htmlFor={inputId}>{copy.followLabel}</label>
        <textarea ref={textarea} id={inputId} rows={1} maxLength={2000} value={input} onChange={event => setInput(event.target.value)} placeholder={t('Reply to CareCompass…', 'CareCompass को जवाब दें…')}
          onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); if (input.trim() && !busy) onSend(input.trim()); } }}/>
        <div className="care-chat-actions"><span className="care-chat-meta"><CareForChip hindi={hindi}/><span className="small muted">{t('English, हिंदी or Hinglish', 'English, हिंदी या Hinglish')}</span></span><div className="care-send-actions"><VoiceInput copy={copy} hindi={hindi} disabled={busy} onTranscript={setInput}/>{busy ? <button type="button" className="care-send care-stop" onClick={onStop} aria-label={t('Stop response', 'जवाब रोकें')}><Square size={15} fill="currentColor"/></button> : <button type="submit" className="care-send" disabled={!input.trim()} aria-label={t('Send message', 'संदेश भेजें')}><ArrowUp size={20}/></button>}</div></div>
      </>}</div>
      <p className="care-chat-footnote">{t('Care navigation, not a diagnosis. Review the recommendation before booking.', 'यह देखभाल का मार्गदर्शन है, निदान नहीं। बुकिंग से पहले सुझाव देखें।')}</p>
    </form>}
  </section>;
}

const ChatMessage = memo(function ChatMessage({ message, copy, hindi, animate, latest }: { message: Message; copy: Copy; hindi: boolean; animate: boolean; latest: boolean }) {
  return <li className={`chat-bubble ${message.role}`} data-animate={animate}>
    <span className="chat-bubble-from">{message.role === 'user' ? (hindi ? 'आप' : 'You') : 'CareCompass'}</span>
    <p>{message.content}</p>
    {message.role === 'assistant' ? <div className="care-message-actions"><CopyMessage text={message.content} hindi={hindi}/>{latest ? <ReadAloud text={message.content} copy={copy} hindi={hindi} autoPlay={false}/> : null}</div> : null}
  </li>;
});

function CopyMessage({ text, hindi }: { text: string; hindi: boolean }) {
  const [copied, setCopied] = useState(false), [failed, setFailed] = useState(false);
  useEffect(() => { if (!copied) return; const timer = setTimeout(() => setCopied(false), 1800); return () => clearTimeout(timer); }, [copied]);
  return <button type="button" className="care-copy-message" aria-label={copied ? (hindi ? 'कॉपी हो गया' : 'Copied') : (hindi ? 'जवाब कॉपी करें' : 'Copy response')} onClick={async () => { try { await navigator.clipboard.writeText(text); setCopied(true); setFailed(false); } catch { setFailed(true); } }}>{copied ? <Check size={14}/> : <CopyIcon size={14}/>}<span>{failed ? (hindi ? 'कॉपी नहीं हुआ' : 'Copy unavailable') : copied ? (hindi ? 'कॉपी हो गया' : 'Copied') : (hindi ? 'कॉपी करें' : 'Copy')}</span></button>;
}
