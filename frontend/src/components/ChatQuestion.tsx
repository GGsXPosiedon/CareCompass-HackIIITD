import { ArrowUp, CornerDownLeft, MessageCircleQuestion, Pencil } from 'lucide-react';
import { useContext, useEffect, useId, useRef, useState } from 'react';
import type { Copy } from '../i18n';
import type { Message, TriageResponse } from '../types';
import { ReadAloud, VoiceInput } from './Voice';
import { VoiceComposerSlot } from './VoiceComposerSlot';
import { VoiceSessionActiveContext } from '../voice/language';

// Chat-style follow-up: the question "pops up" in the answer bar, the way ChatGPT/Claude ask clarifying
// questions. Tapping an option (or pressing its number) answers immediately; "Something else" opens a
// free-text answer. The conversation so far stays visible above.
export function AskCard({ copy, hindi, question, intro, answerOptions, asked, input, setInput, onAnswer, onBack, busy, error }: {
  copy: Copy; hindi: boolean; question: string; intro?: string; answerOptions: string[]; asked: number;
  input: string; setInput: (value: string) => void; onAnswer: (text: string) => void; onBack: () => void; busy: boolean; error: string;
}) {
  const voiceActive = useContext(VoiceSessionActiveContext);
  const t = (en: string, hi: string) => hindi ? hi : en;
  const options = answerOptions;
  const [custom, setCustom] = useState(options.length === 0);
  const [picked, setPicked] = useState<string | null>(null);
  const card = useRef<HTMLFormElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const titleId = useId(); const errorId = useId();

  useEffect(() => { setCustom(options.length === 0); setPicked(null); card.current?.querySelector<HTMLElement>('.ask-option, textarea')?.focus({ preventScroll: true }); }, [question, answerOptions.join('|')]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (custom) textarea.current?.focus(); }, [custom]);

  function choose(option: string) { if (busy) return; setPicked(option); onAnswer(option); }
  function onKey(event: React.KeyboardEvent) {
    if (busy || (event.target as HTMLElement).tagName === 'TEXTAREA') return;
    const n = Number(event.key);
    if (n >= 1 && n <= options.length) { event.preventDefault(); choose(options[n - 1]); }
    else if (n === options.length + 1 && options.length) { event.preventDefault(); setCustom(true); }
    else if (event.key === 'Escape') { event.preventDefault(); onBack(); }
  }

  return <form ref={card} className="ask-card" aria-labelledby={titleId} onKeyDown={onKey} onSubmit={e => { e.preventDefault(); if (input.trim() && !busy) onAnswer(input.trim()); }}>
      <div className="ask-head">
        <span className="ask-badge"><MessageCircleQuestion size={15} />{t(`Question ${asked}`, `सवाल ${asked}`)}</span>
        <div className="ask-head-actions"><ReadAloud text={`${intro ?? ''} ${question}`.trim()} copy={copy} hindi={hindi} /><button type="button" className="ask-edit" onClick={onBack} disabled={busy}><Pencil size={14} />{copy.edit}</button></div>
      </div>
      {intro ? <p className="small muted">{intro}</p> : null}
      <h2 id={titleId} className="ask-question">{question}</h2>
      {options.length ? <div className="ask-options" role="group" aria-label={t('Answer options', 'जवाब के विकल्प')}>
        {options.map((option, i) => <button type="button" key={option} className={`ask-option${picked === option ? ' picked' : ''}`} onClick={() => choose(option)} disabled={busy} aria-keyshortcuts={String(i + 1)}>
          <kbd aria-hidden="true">{i + 1}</kbd><span>{option}</span>{busy && picked === option ? <span className="spinner" aria-hidden="true" /> : <CornerDownLeft size={15} className="ask-option-enter" aria-hidden="true" />}
        </button>)}
        {!custom ? <button type="button" className="ask-option ask-other" onClick={() => setCustom(true)} disabled={busy} aria-keyshortcuts={String(options.length + 1)}>
          <kbd aria-hidden="true">{options.length + 1}</kbd><span>{t('Something else…', 'कुछ और…')}</span>
        </button> : null}
      </div> : null}
      {custom || voiceActive ? <div className="ask-composer">{voiceActive ? <VoiceComposerSlot/> : <>
        <label className="sr-only" htmlFor={`${titleId}-answer`}>{copy.followLabel}</label>
        <textarea id={`${titleId}-answer`} ref={textarea} rows={2} maxLength={2000} value={input} disabled={busy} placeholder={copy.followPlaceholder}
          aria-invalid={!!error} aria-describedby={error ? errorId : undefined} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); if (input.trim() && !busy) onAnswer(input.trim()); } if (e.key === 'Escape' && options.length) { e.preventDefault(); setCustom(false); } }} />
        <div className="ask-composer-actions"><VoiceInput copy={copy} hindi={hindi} disabled={busy} onTranscript={text => setInput(text.slice(0, 2000))} />
          <button type="submit" className="care-send" disabled={busy || !input.trim()} aria-label={busy ? copy.checking : copy.send}>{busy && !picked ? <span className="spinner" aria-hidden="true" /> : <ArrowUp size={20} />}</button></div>
      </>}</div> : null}
      {error ? <p className="error-message" id={errorId} role="alert">{error}</p> : null}
      <p className="ask-hint">{busy ? copy.checking : options.length ? t(`Press 1–${options.length + 1} to answer · Esc to edit your request`, `जवाब के लिए 1–${options.length + 1} दबाएँ · अनुरोध बदलने के लिए Esc`) : t('Enter to send · Shift+Enter for a new line', 'भेजने के लिए Enter · नई लाइन के लिए Shift+Enter')}</p>
  </form>;
}

export function ChatQuestion({ copy, hindi, result, messages, symptom, input, setInput, onAnswer, onBack, busy, error }: {
  copy: Copy; hindi: boolean; result: TriageResponse; messages: Message[]; symptom: string;
  input: string; setInput: (value: string) => void; onAnswer: (text: string) => void; onBack: () => void; busy: boolean; error: string;
}) {
  const asked = messages.filter(m => m.role === 'assistant').length;
  const thread = messages.slice(0, -1);
  return <section className="chat-question" aria-label={copy.followTitle}>
    <ol className="chat-thread" aria-label={copy.conversation}>
      {thread.map((m, i) => <li key={`${i}-${m.role}`} className={`chat-bubble ${m.role}`}>
        {m.role === 'assistant' ? <span className="chat-bubble-from">CareCompass</span> : null}
        <p>{m.role === 'user' && i === 0 ? symptom : m.content}</p>
      </li>)}
    </ol>
    <AskCard copy={copy} hindi={hindi} question={result.follow_up_question ?? ''} intro={result.reasoning} answerOptions={result.answer_options ?? []} asked={asked} input={input} setInput={setInput} onAnswer={onAnswer} onBack={onBack} busy={busy} error={error}/>
  </section>;
}
