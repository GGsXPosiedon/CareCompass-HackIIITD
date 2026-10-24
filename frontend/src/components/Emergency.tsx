import { ArrowLeft, ExternalLink, Phone, ShieldAlert } from 'lucide-react';
import type { Copy } from '../i18n';
import type { TriageResponse } from '../types';
import { DEMO_MODE } from '../lib/api';
import { ReadAloud } from './Voice';

export function Emergency({ copy, hindi, result, onNew }: { copy: Copy; hindi: boolean; result: TriageResponse; onNew: () => void }) {
  return <section className="emergency-view"><div className="emergency-heading"><ShieldAlert size={35} strokeWidth={1.6} /><h1 tabIndex={-1}>{copy.emergencyTitle}</h1><p>{copy.emergencyIntro}</p></div>
    <div className="emergency-card"><h2>{copy.emergencyReason}</h2><p>{result.reasoning}</p>{result.red_flags.length ? <ul>{result.red_flags.map(flag => <li key={flag}>{flag}</li>)}</ul> : null}<p>{copy.emergencySkipped}</p><ReadAloud text={`${copy.emergencyTitle} ${copy.emergencyBody}`} hindi={hindi} copy={copy} /></div>
    <p className="emergency-instructions">{copy.emergencyBody}</p><a className="button emergency-button" href="tel:112"><Phone size={20} />{copy.emergencyCall}</a>
    <a className="text-button emergency-source" href="https://112.gov.in/" target="_blank" rel="noreferrer">112 India <ExternalLink size={14} /></a>
    {DEMO_MODE ? <p className="small muted">{copy.emergencyDemo}</p> : null}<button className="text-button emergency-back" onClick={onNew}><ArrowLeft size={17} />{copy.startOver}</button>
  </section>;
}
