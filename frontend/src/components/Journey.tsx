import { ArrowRight, Check, MapPin, MessageCircle, ShieldCheck, Stethoscope } from 'lucide-react';
import type { Copy } from '../i18n';
import type { Location } from '../types';

export function Journey({ copy, active = 0, location }: { copy: Copy; active?: number; location: Location }) {
  const stops = [
    { title: copy.journeyDescribe, body: copy.journeyDescribeBody, Icon: MessageCircle },
    { title: copy.journeyCare, body: copy.journeyCareBody, Icon: Stethoscope },
    { title: copy.journeyBook, body: copy.journeyBookBody, Icon: MapPin },
  ];
  return <aside className="journey-panel" aria-labelledby="journey-title">
    <div className="journey-heading"><h2 id="journey-title">{copy.careJourney}</h2><span className="compass-small" aria-hidden="true"><ArrowRight size={22} /></span></div>
    <p className="muted">{copy.journeyIntro}</p>
    <ol className="journey-stops">{stops.map(({ title, body, Icon }, index) => <li key={title} className={index <= active ? 'reached' : ''}>
      <span className="journey-node" aria-hidden="true">{index < active ? <Check size={16} /> : <Icon size={18} />}</span>
      <div><h3>{title}</h3><p>{body}</p></div>
    </li>)}</ol>
    <div className="journey-location"><MapPin size={17} /><div><span className="small muted">{copy.locationDemo}</span><p>{location.lat === 0 ? copy.outside : location.label}</p></div></div>
    <p className="journey-safety"><ShieldCheck size={18} /><span>{copy.safetyNote}</span></p>
  </aside>;
}
