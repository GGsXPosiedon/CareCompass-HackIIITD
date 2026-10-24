import { MapPin, MessageCircle, ShieldCheck } from 'lucide-react';
import type { Copy } from '../i18n';
import { careLabel } from '../i18n';
import { formatDate, formatTime } from '../lib/flow';
import type { Caregiver, CareType, Location } from '../types';

export function RequestSummary({ copy, symptom, location, answers }: { copy: Copy; symptom: string; location: Location; answers: number }) {
  return <aside className="summary-panel"><h2>{copy.yourRequest}</h2><div className="request-quote"><MessageCircle size={19} /><p>{symptom}</p></div><dl className="summary-list"><div><dt>{copy.selectedLocation}</dt><dd><MapPin size={15} />{location.lat === 0 ? copy.outside : location.label}</dd></div><div><dt>{copy.answerCount}</dt><dd>{answers || copy.noAnswers}</dd></div></dl><p className="journey-safety"><ShieldCheck size={18} />{copy.safetyNote}</p></aside>;
}
export function BookingSummary({ copy, hindi, caregiver, careType, date, slot, location }: { copy: Copy; hindi: boolean; caregiver: Caregiver; careType: CareType; date: string; slot: string; location: Location }) {
  return <aside className="summary-panel booking-summary"><h2>{copy.summary}</h2><dl className="summary-list"><div><dt>{copy.service}</dt><dd>{careLabel(careType, hindi)}</dd></div><div><dt>{copy.provider}</dt><dd>{caregiver.name}</dd></div><div><dt>{copy.date}</dt><dd>{formatDate(date, hindi)}</dd></div><div><dt>{copy.time}</dt><dd>{slot ? formatTime(slot, hindi) : '—'}</dd></div><div><dt>{copy.selectedLocation}</dt><dd>{careType === 'teleconsultation' ? copy.online : location.label}</dd></div></dl><p className="journey-safety"><ShieldCheck size={18} />{copy.safetyNote}</p></aside>;
}
