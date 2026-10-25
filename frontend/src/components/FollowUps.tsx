import { ArrowLeft, ArrowRight, MessageCircle } from 'lucide-react';
import type { Copy } from '../i18n';
import type { Location, Message, TriageResponse } from '../types';
import { ReadAloud, VoiceInput } from './Voice';
import { RequestSummary } from './Summary';

export function FollowUps({ copy, hindi, result, messages, input, setInput, onSubmit, onBack, busy, error, symptom, location }: {
  copy: Copy; hindi: boolean; result: TriageResponse; messages: Message[]; input: string; setInput: (value: string) => void;
  onSubmit: () => void; onBack: () => void; busy: boolean; error: string; symptom: string; location: Location;
}) {
  return <><button className="text-button back-button" disabled={busy} onClick={onBack}><ArrowLeft size={17} />{copy.edit}</button>
    <div className="page-heading"><h1 tabIndex={-1}>{copy.followTitle}</h1><p>{copy.followIntro}</p></div>
    <div className="care-grid"><section className="request-panel follow-panel">
      <div className="question-meta"><span><MessageCircle size={18} />CareCompass</span><ReadAloud text={result.follow_up_question ?? ''} copy={copy} hindi={hindi} /></div>
      {result.reasoning ? <p className="small muted">{result.reasoning}</p> : null}
      <h2 className="question-title">{result.follow_up_question}</h2>
      {result.answer_options?.length ? <div className="answer-options">{result.answer_options.map(option => <button type="button" key={option} className={`answer-option ${input === option ? 'chosen' : ''}`} aria-pressed={input === option} onClick={() => setInput(option)} disabled={busy}>{option}</button>)}</div> : null}
      <form onSubmit={e => { e.preventDefault(); onSubmit(); }}><label className="field-label" htmlFor="answer">{copy.followLabel}</label><textarea id="answer" rows={2} value={input} onChange={e => setInput(e.target.value)} placeholder={copy.followPlaceholder} maxLength={2000} disabled={busy} aria-invalid={!!error} aria-describedby={error ? 'answer-error' : undefined} />
        <div className="follow-voice"><VoiceInput copy={copy} hindi={hindi} disabled={busy} onTranscript={text => setInput(text.slice(0, 2000))} /></div>
        {error ? <p className="error-message" id="answer-error" role="alert">{error}</p> : null}
        <button type="submit" className="button primary full-width" disabled={busy}>{busy ? <span className="spinner" aria-hidden="true" /> : null}{busy ? copy.checking : copy.send}{!busy ? <ArrowRight size={18} /> : null}</button>
      </form>
      <details className="conversation"><summary>{copy.conversation}</summary><div>{messages.slice(0, -1).map((message, index) => <p key={`${index}-${message.role}`} className={message.role === 'user' ? 'user-message' : 'assistant-message'}><span>{message.role === 'assistant' ? 'CareCompass' : copy.followLabel}</span>{message.content}</p>)}</div></details>
    </section><RequestSummary copy={copy} symptom={symptom} location={location} answers={Math.max(0, messages.filter(m => m.role === 'user').length - 1)} /></div>
  </>;
}
