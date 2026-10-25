import { ArrowRight, House, Stethoscope, HeartPulse, Video, ShieldCheck } from 'lucide-react';
import { scenarios } from '../data';
import type { Copy } from '../i18n';
import type { Language, Location } from '../types';
import { Journey } from './Journey';
import { VoiceInput } from './Voice';
import { ChatIntake } from './ChatIntake';

export interface IntakeProps {
  copy: Copy; hindi: boolean; language: Language; input: string; setInput: (input: string) => void;
  location: Location; busy: boolean; error: string; onSubmit: () => void;
  onLocation?: () => void; compact?: boolean;
}
export function Intake(props: IntakeProps) {
  const { copy, hindi, language, input, setInput, location, busy, error, onSubmit } = props;
  if (props.compact) return <ChatIntake {...props}/>;
  const services = [
    { title: copy.serviceParamedic, description: copy.serviceParamedicDesc, Icon: House },
    { title: copy.serviceNurse, description: copy.serviceNurseDesc, Icon: HeartPulse },
    { title: copy.serviceDoctor, description: copy.serviceDoctorDesc, Icon: Video },
    { title: copy.serviceSpecialist, description: copy.serviceSpecialistDesc, Icon: Stethoscope },
  ];
  return <>
    <div className="page-heading"><h1 tabIndex={-1}>{copy.headline}</h1><p>{copy.intro}</p></div>
    <div className="care-grid">
      <section className="request-panel" aria-label={copy.findCare}>
        <form onSubmit={e => { e.preventDefault(); onSubmit(); }}>
          <label className="field-label" htmlFor="symptoms">{copy.inputLabel}</label>
          <div className="symptom-composer"><textarea id="symptoms" value={input} onChange={e => setInput(e.target.value)} placeholder={copy.placeholder} rows={3} maxLength={2000} disabled={busy} aria-describedby={`input-hint${error ? ' intake-error' : ''}`} aria-invalid={!!error} />
            <div className="composer-bottom"><VoiceInput copy={copy} hindi={hindi} disabled={busy} onTranscript={text => setInput(`${input}${input ? ' ' : ''}${text}`.slice(0, 2000))} /><span className="character-count" aria-hidden="true">{input.length}/2000</span></div>
          </div>
          <p id="input-hint" className="small muted">{copy.hint}</p>
          <div className="examples"><span className="small muted">{copy.examples}</span><div className="example-buttons">{scenarios.map(s => <button className="example-button" type="button" key={s.id} onClick={() => setInput(hindi ? s.textHi : language === 'hinglish' ? s.hinglish : s.text)} disabled={busy}>{hindi ? s.hi : s.en}<ArrowRight size={14} /></button>)}</div></div>
          {error ? <p className="error-message" role="alert" id="intake-error">{error}</p> : null}
          <button type="submit" className="button primary full-width" disabled={busy}>{busy ? <span className="spinner" aria-hidden="true" /> : null}{busy ? copy.checking : copy.continue}{!busy ? <ArrowRight size={19} /> : null}</button>
          <p className="input-safety small"><ShieldCheck size={16} />{copy.safetyNote}</p>
          <p className="voice-disclosure">{copy.voiceNotice}</p>
        </form>
      </section>
      <Journey copy={copy} location={location} />
    </div>
    <section className="services-section" aria-labelledby="services-heading"><div className="section-heading"><h2 id="services-heading">{copy.servicesTitle}</h2><p>{copy.servicesIntro}</p></div><div className="service-list">{services.map(({ title, description, Icon }) => <article className="service-item" key={title}><Icon size={25} strokeWidth={1.5} /><h3>{title}</h3><p>{description}</p></article>)}</div></section>
  </>;
}
