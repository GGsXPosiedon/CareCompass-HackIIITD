import { ArrowLeft, ArrowRight, Check, ChevronRight, Clock3, MapPin, Star, Video } from 'lucide-react';
import type { Copy } from '../i18n';
import type { Caregiver, Location, TriageResponse } from '../types';
import { careLabel, urgencyLabel } from '../i18n';
import { DEMO_MODE } from '../lib/api';
import { availableSlots, formatTime, localDate } from '../lib/flow';

export function Avatar({ caregiver }: { caregiver: Caregiver }) { return <span className={`avatar ${caregiver.tint}`} aria-hidden="true">{caregiver.initials}</span>; }
export function Caregivers({ copy, hindi, profiles, result, selected, setSelected, filter, setFilter, location, onBack, onContinue }: {
  copy: Copy; hindi: boolean; profiles: Caregiver[]; result: TriageResponse; selected: Caregiver | null;
  setSelected: (caregiver: Caregiver) => void; filter: string; setFilter: (value: string) => void; location: Location; onBack: () => void; onContinue: () => void;
}) {
  const visible = profiles.filter(c => filter === 'all' || c.languages.includes(filter));
  const languages = [...new Set(profiles.flatMap(c => c.languages))];
  return <><button className="text-button back-button" onClick={onBack}><ArrowLeft size={17} />{copy.back}</button><div className="page-heading"><h1 tabIndex={-1}>{copy.caregiverTitle}</h1><p>{copy.caregiverIntro}</p></div>
    <div className="provider-layout"><section><div className="provider-toolbar"><p>{visible.length} {copy.matchLabel.toLowerCase()}</p><label>{copy.filterLanguage}<select value={filter} onChange={e => setFilter(e.target.value)}><option value="all">{copy.allLanguages}</option>{languages.map(lang => <option key={lang} value={lang}>{lang === 'Hindi' ? copy.hindi : lang === 'English' ? copy.english : lang}</option>)}</select></label></div>
      {DEMO_MODE ? <p className="small muted provider-disclosure">{copy.profilesDemo}</p> : null}
      <div className="provider-list" role="group" aria-label={copy.matchLabel}>{visible.map(c => {
        const chosen = selected?.id === c.id;
        const match = result.matched_caregivers.find(m => m.caregiver_id === c.id);
        const nextSlot = availableSlots(c.slots, localDate())[0];
        const unavailable = result.urgency === 'same_day' && !nextSlot;
        return <article className={`provider-card ${chosen ? 'chosen' : ''}`} key={c.id}><div className="provider-top"><Avatar caregiver={c} /><div className="provider-identity"><h2>{c.name}</h2><p>{hindi ? c.roleHi : c.role} · {c.experience} {copy.years}</p></div><span className="rating"><Star size={14} fill="currentColor" />{c.rating.toFixed(1)}<span className="sr-only"> / 5</span></span></div>
          <div className="provider-meta"><span>{c.careType === 'gp_teleconsult' ? <Video size={15} /> : <MapPin size={15} />}{c.careType === 'gp_teleconsult' ? copy.online : `${c.distance} ${copy.km}`}</span><span>{c.languages.map(l => l === 'Hindi' ? copy.hindi : l === 'English' ? copy.english : l).join(', ')}</span><span>{c.reviews} {copy.reviews}</span></div>
          <div className="skills">{(hindi ? c.skillsHi : c.skills).map(skill => <span key={skill}>{skill}</span>)}</div>
          <p className="provider-availability"><Clock3 size={14} />{nextSlot ? `${copy.nextSlot}: ${copy.today.toLowerCase()}, ${formatTime(nextSlot, hindi)}` : result.urgency === 'same_day' ? copy.noTimesToday : `${copy.nextSlot}: ${copy.tomorrow.toLowerCase()}`}</p>
          <div className="provider-bottom"><p><span>{copy.matchReason}: </span>{match?.reason}</p><button className={`button ${chosen ? 'selected-button' : 'secondary'}`} disabled={unavailable || !c.slots.length} aria-pressed={chosen} aria-label={`${chosen ? copy.selected : copy.choose} ${c.name}`} onClick={() => setSelected(c)}>{chosen ? <Check size={17} /> : null}{chosen ? copy.selected : copy.choose}{!chosen ? <ChevronRight size={16} /> : null}</button></div>
        </article>;
      })}</div>
      {!visible.length ? <div className="empty-state"><p>{copy.noFilter}</p><button className="button secondary" onClick={() => setFilter('all')}>{copy.clearFilter}</button></div> : null}
    </section><aside className="selection-panel"><h2>{copy.summary}</h2><dl className="summary-list"><div><dt>{copy.service}</dt><dd>{result.care_type ? careLabel(result.care_type, hindi) : '—'}</dd></div><div><dt>{copy.urgency}</dt><dd>{result.urgency ? urgencyLabel(result.urgency, hindi) : '—'}</dd></div><div><dt>{copy.selectedLocation}</dt><dd>{location.label}</dd></div><div><dt>{copy.provider}</dt><dd>{selected?.name ?? '—'}</dd></div></dl><button className="button primary full-width" onClick={onContinue} disabled={!selected}>{copy.chooseContinue}<ArrowRight size={18} /></button>{!selected ? <p className="small muted">{copy.selectCaregiver}</p> : null}</aside></div>
  </>;
}
