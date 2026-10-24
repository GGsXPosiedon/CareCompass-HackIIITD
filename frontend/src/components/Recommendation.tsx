import { ArrowLeft, ArrowRight, Clock3, MapPin, Video } from 'lucide-react';
import type { Copy } from '../i18n';
import { careLabel, urgencyLabel } from '../i18n';
import type { Location, TriageResponse } from '../types';
import { DEMO_MODE } from '../lib/api';
import { RequestSummary } from './Summary';
import { ReadAloud } from './Voice';

export function Recommendation({ copy, hindi, result, symptom, location, answers, busy, error, onContinue, onBack, onLocation }: { copy: Copy; hindi: boolean; result: TriageResponse; symptom: string; location: Location; answers: number; busy: boolean; error: string; onContinue: () => void; onBack: () => void; onLocation: () => void }) {
  if (!result.care_type || !result.urgency) return null;
  const online = result.care_type === 'gp_teleconsult';
  return <><button className="text-button back-button" disabled={busy} onClick={onBack}><ArrowLeft size={17} />{copy.edit}</button><div className="page-heading"><h1 tabIndex={-1}>{copy.resultTitle}</h1><p>{copy.resultIntro}</p></div>
    <div className="care-grid"><section className="request-panel result-panel">
      <span className={`status-pill ${result.urgency === 'same_day' ? 'warning' : 'neutral'}`}><Clock3 size={14} />{urgencyLabel(result.urgency, hindi)}</span>
      <p className="small muted care-label">{copy.careType}</p><h2 className="care-result">{careLabel(result.care_type, hindi)}</h2>
      <p className="care-setting">{online ? <Video size={18} /> : <MapPin size={18} />}{online ? copy.online : location.label}</p>
      <div className="reason-block"><h3>{copy.why}</h3><p>{result.reasoning}</p><ReadAloud text={`${careLabel(result.care_type, hindi)}. ${result.reasoning}`} copy={copy} hindi={hindi} /></div>
      {DEMO_MODE ? <p className="small muted">{copy.preset}</p> : null}
      {error ? <p role="alert" className="error-message">{error}</p> : null}
      {!result.matched_caregivers.length ? <div className="empty-state compact"><h3>{copy.noMatches}</h3><p>{copy.noMatchesBody}</p><button className="button secondary" onClick={onLocation}>{copy.changeArea}</button></div> : <button className="button primary full-width" disabled={busy} onClick={onContinue}>{busy ? <span className="spinner" aria-hidden="true" /> : null}{busy ? copy.loadingProfiles : error ? copy.retry : copy.viewCaregivers}{!busy ? <ArrowRight size={18} /> : null}</button>}
    </section><RequestSummary copy={copy} symptom={symptom} location={location} answers={answers} /></div></>;
}
