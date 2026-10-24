import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, ChevronDown, Compass, Globe2, HelpCircle, MapPin, Menu, MessageCircle, ShieldCheck, Stethoscope, X } from 'lucide-react';
import { getCopy } from './i18n';
import { emergencyExample, locations, scenarios } from './data';
import { createBooking, DEMO_MODE, getCaregivers, intake } from './lib/api';
import { availableSlots, localDate, nextView } from './lib/flow';
import type { Booking, Caregiver, IntakeRequest, Language, Location, Message, TriageResponse } from './types';
import { Intake } from './components/Intake';
import { FollowUps } from './components/FollowUps';
import { Recommendation } from './components/Recommendation';
import { Caregivers } from './components/Caregivers';
import { BookingForm, Bookings, Confirmation } from './components/Booking';
import { Emergency } from './components/Emergency';
import { Modal } from './components/Modal';

type View = 'intake' | 'questions' | 'recommendation' | 'caregivers' | 'booking' | 'confirmation' | 'bookings' | 'emergency';
type ModalView = 'location' | 'help' | 'how' | null;
export default function App({ embedded = false, externalLanguage, patientName, externalBookings, onStartCare, onViewBookings }: { embedded?: boolean; externalLanguage?: Language; patientName?: string; externalBookings?: boolean; onStartCare?: () => void; onViewBookings?: () => void }) {
  const [view, setView] = useState<View>('intake');
  const [language, setLanguage] = useState<Language>('en');
  const hindi = language === 'hi'; const copy = getCopy(hindi);
  const [input, setInput] = useState('');
  const [answer, setAnswer] = useState('');
  const [person, setPerson] = useState('family');
  const [location, setLocation] = useState<Location>(locations[0]);
  const [draftLocation, setDraftLocation] = useState<Location>(locations[0]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [result, setResult] = useState<TriageResponse | null>(null);
  const [profiles, setProfiles] = useState<Caregiver[]>([]);
  const [selected, setSelected] = useState<Caregiver | null>(null);
  const [filter, setFilter] = useState('all');
  const [date, setDate] = useState(localDate());
  const [slot, setSlot] = useState('');
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [confirmed, setConfirmed] = useState<Booking | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [modal, setModal] = useState<ModalView>(null);
  const [menu, setMenu] = useState(false);
  const generation = useRef(0); const locked = useRef(false);
  const [announcement, setAnnouncement] = useState('');
  const main = useRef<HTMLElement>(null);
  const MainTag = embedded ? 'section' : 'main';

  useEffect(() => {
    if (!embedded) document.documentElement.lang = hindi ? 'hi' : 'en';
  }, [hindi, embedded]);
  useEffect(() => { if (externalLanguage) updateLanguage(externalLanguage); }, [externalLanguage]);
  useEffect(() => {
    if (externalBookings) { generation.current++; locked.current = false; setBusy(false); setError(''); setView('bookings'); }
    else if (embedded && view === 'bookings') setView('intake');
  }, [externalBookings]);
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
    if (view !== 'intake') main.current?.querySelector<HTMLElement>('h1')?.focus({ preventScroll: true });
  }, [view]);
  useEffect(() => {
    if (view === 'questions' && result?.follow_up_question) setAnnouncement(result.follow_up_question);
  }, [result, view]);

  function reset() {
    generation.current++; locked.current = false;
    setBusy(false); setView('intake'); setInput(''); setAnswer(''); setMessages([]); setResult(null); setProfiles([]); setSelected(null); setSlot(''); setError(''); setFilter('all'); setMenu(false); setAnnouncement('');
    onStartCare?.();
  }
  function edit() {
    generation.current++; locked.current = false;
    setBusy(false); setView('intake'); setAnswer(''); setMessages([]); setResult(null); setProfiles([]); setSelected(null); setError(''); setSlot('');
  }
  function updateLanguage(value: Language) {
    setLanguage(value);
    // A response's language belongs to its request; restart unfinished intake when switching.
    if (messages.length && view !== 'confirmation' && view !== 'bookings') edit();
    setError('');
  }
  async function submit(override?: { text: string; location?: Location; simulateError?: boolean }) {
    if (locked.current) return;
    const followUp = view === 'questions' && !override;
    const text = (override?.text ?? (followUp ? answer : input)).trim();
    if (!text) { setError(copy.blank); return; }
    if (text.length > 2000) { setError(copy.tooLong); return; }
    const history = followUp ? messages : [];
    const requestLocation = override?.location ?? location;
    const relation = `${patientName ? `${patientName} (demo) · ` : ''}${person === 'me' ? copy.me : copy.family}`;
    const payload: IntakeRequest = { user_input: followUp ? text : `${relation}: ${text}`, language, location: { lat: requestLocation.lat, lng: requestLocation.lng }, conversation_history: history };
    const current = ++generation.current; locked.current = true; setBusy(true); setError('');
    if (!followUp) { setInput(text); setLocation(requestLocation); setMessages([]); setResult(null); setSelected(null); setProfiles([]); setView('intake'); }
    try {
      if (override?.simulateError) throw new Error('DEMO_ERROR');
      const response = await intake(payload);
      if (current !== generation.current) return;
      const nextMessages: Message[] = [...history, { role: 'user', content: payload.user_input }];
      if (response.follow_up_question) nextMessages.push({ role: 'assistant', content: response.follow_up_question });
      setMessages(nextMessages); setResult(response); setAnswer(''); setView(nextView(response));
    } catch { if (current === generation.current) setError(copy.genericError); }
    finally { if (current === generation.current) { setBusy(false); locked.current = false; } }
  }
  async function loadProfiles() {
    if (!result || locked.current) return;
    const current = ++generation.current; locked.current = true; setBusy(true); setError('');
    try {
      const data = await getCaregivers(result.matched_caregivers.map(m => m.caregiver_id));
      if (current !== generation.current) return;
      const ranked = result.matched_caregivers.map(m => data.find(c => c.id === m.caregiver_id));
      if (ranked.some(c => !c || c.careType !== result.care_type)) throw new Error('MISSING_PROFILE');
      setProfiles(ranked as Caregiver[]); setFilter('all'); setSelected(null); setView('caregivers');
    } catch { if (current === generation.current) setError(copy.profileError); }
    finally { if (current === generation.current) { setBusy(false); locked.current = false; } }
  }
  async function confirm() {
    if (!selected || !result?.care_type || locked.current) return;
    if (!slot || !availableSlots(selected.slots, date).includes(slot)) { setSlot(''); setError(copy.chooseSlot); return; }
    const current = ++generation.current; locked.current = true; setBusy(true); setError('');
    try {
      const response = await createBooking({ caregiver_id: selected.id, slot, date, location: { lat: location.lat, lng: location.lng } });
      if (current !== generation.current) return;
      const booking: Booking = { id: response.id, caregiver: selected, date, slot, location, careType: result.care_type, demo: DEMO_MODE };
      setBookings(previous => [booking, ...previous]); setConfirmed(booking); setView('confirmation');
    } catch { if (current === generation.current) setError(copy.genericError); }
    finally { if (current === generation.current) { setBusy(false); locked.current = false; } }
  }
  function showLocation() { setDraftLocation(location); setModal('location'); setMenu(false); }
  function saveLocation() {
    const changed = location.label !== draftLocation.label; setLocation(draftLocation); setModal(null);
    if (changed && view !== 'intake' && view !== 'bookings' && view !== 'confirmation') edit();
  }
  function showBookings() { setMenu(false); setError(''); setView('bookings'); onViewBookings?.(); }
  const progress = view === 'intake' || view === 'questions' ? 0 : view === 'recommendation' || view === 'caregivers' ? 1 : 2;
  const displayProgress = view !== 'bookings' && view !== 'emergency';

  return <><a className="skip-link" href="#main">{copy.skip}</a><header className="site-header"><div className="header-inner">
    <button className="brand" onClick={reset} disabled={busy} aria-label="CareCompass home"><img src="/compass.svg" width="33" height="33" alt="" /><span>CareCompass</span></button>
    <button className="header-location" onClick={showLocation} disabled={busy}><MapPin size={18} /><span>{location.lat === 0 ? copy.outside : location.label}<small>{copy.locationDemo}</small></span><ChevronDown size={15} /></button>
    <nav className="desktop-nav" aria-label="Main"><button className={view === 'bookings' ? '' : 'nav-active'} onClick={() => { if (view === 'bookings' || view === 'confirmation') reset(); else if (view !== 'intake') edit(); }} disabled={busy}>{copy.findCare}</button><button className={view === 'bookings' ? 'nav-active' : ''} onClick={showBookings} disabled={busy}>{copy.bookings}{bookings.length ? <span className="nav-count">{bookings.length}</span> : null}</button><button onClick={() => setModal('how')}>{copy.howItWorks}</button></nav>
    <div className="header-right"><label className="language-control"><Globe2 size={17} /><span className="sr-only">{copy.language}</span><select aria-label={copy.language} value={language} onChange={e => updateLanguage(e.target.value as Language)} disabled={busy}><option value="en">English</option><option value="hi">हिंदी</option><option value="hinglish">Hinglish</option><option value="auto">Auto</option></select></label><button className="help-button" onClick={() => setModal('help')}><HelpCircle size={18} /><span>{copy.help}</span></button><button className="icon-button menu-toggle" onClick={() => setMenu(!menu)} aria-expanded={menu} aria-label={menu ? copy.close : copy.menu}>{menu ? <X size={22} /> : <Menu size={22} />}</button></div>
  </div>{menu ? <nav className="mobile-nav" aria-label="Mobile"><button onClick={() => { reset(); setMenu(false); }} disabled={busy}>{copy.findCare}</button><button onClick={showBookings} disabled={busy}>{copy.bookings}</button><button onClick={showLocation} disabled={busy}>{copy.location}</button><button onClick={() => { setModal('how'); setMenu(false); }}>{copy.howItWorks}</button><button onClick={() => { setModal('help'); setMenu(false); }}>{copy.help}</button></nav> : null}</header>
  <MainTag id={embedded ? undefined : 'main'} className="main-container" ref={main}>
    <div className="context-bar">{displayProgress ? <ol className="progress" aria-label={hindi ? 'देखभाल की प्रगति' : 'Care progress'}>{[copy.describe, copy.recommendation, copy.book].map((step, index) => <li key={index} className={index === progress ? 'current' : index < progress ? 'complete' : ''} aria-current={index === progress ? 'step' : undefined}><span className="progress-mark">{index < progress ? <Check size={12} /> : <span />}</span>{step}{index < 2 ? <span className="progress-line" aria-hidden="true" /> : null}</li>)}</ol> : <span />}{DEMO_MODE ? <span className="demo-label"><span />{copy.demo}</span> : null}</div>
    {view === 'intake' ? <Intake copy={copy} hindi={hindi} language={language} input={input} setInput={value => { setInput(value); setError(''); }} person={person} setPerson={setPerson} location={location} busy={busy} error={error} onSubmit={() => void submit()} /> : null}
    {view === 'questions' && result ? <FollowUps copy={copy} hindi={hindi} result={result} messages={messages} input={answer} setInput={value => { setAnswer(value); setError(''); }} onSubmit={() => void submit()} onBack={edit} busy={busy} error={error} symptom={input} location={location} /> : null}
    {view === 'recommendation' && result ? <Recommendation copy={copy} hindi={hindi} result={result} symptom={input} location={location} answers={Math.max(0, messages.filter(m => m.role === 'user').length - 1)} busy={busy} error={error} onContinue={() => void loadProfiles()} onBack={edit} onLocation={showLocation} /> : null}
    {view === 'caregivers' && result ? <Caregivers copy={copy} hindi={hindi} profiles={profiles} result={result} selected={selected} setSelected={setSelected} filter={filter} setFilter={value => { setFilter(value); if (selected && value !== 'all' && !selected.languages.includes(value)) setSelected(null); }} location={location} onBack={() => setView('recommendation')} onContinue={() => { if (selected) { setDate(localDate()); setSlot(''); setError(''); setView('booking'); } }} /> : null}
    {view === 'booking' && selected && result?.care_type ? <BookingForm copy={copy} hindi={hindi} caregiver={selected} careType={result.care_type} location={location} date={date} setDate={value => { setDate(value); setSlot(''); setError(''); }} slot={slot} setSlot={value => { setSlot(value); setError(''); }} sameDay={result.urgency === 'same_day'} busy={busy} error={error} onBack={() => { setError(''); setView('caregivers'); }} onConfirm={() => void confirm()} /> : null}
    {view === 'confirmation' && confirmed ? <Confirmation copy={copy} hindi={hindi} booking={confirmed} onBookings={showBookings} onNew={reset} /> : null}
    {view === 'bookings' ? <Bookings copy={copy} hindi={hindi} bookings={bookings} onNew={reset} /> : null}
    {view === 'emergency' && result ? <Emergency copy={copy} hindi={hindi} result={result} onNew={reset} /> : null}
    {DEMO_MODE ? <details className="demo-tools"><summary>{copy.demoTools}</summary><p className="small muted">{copy.demoToolsNote}</p><div><button className="text-button" disabled={busy} onClick={() => void submit({ text: hindi ? emergencyExample.hi : emergencyExample.en })}>{copy.emergencyExample}<ArrowRight size={15} /></button><button className="text-button" disabled={busy} onClick={() => void submit({ text: hindi ? scenarios[0].textHi : scenarios[0].text, location: locations[3] })}>{copy.emptyExample}<ArrowRight size={15} /></button><button className="text-button" disabled={busy} onClick={() => void submit({ text: hindi ? scenarios[0].textHi : scenarios[0].text, simulateError: true })}>{copy.errorExample}<ArrowRight size={15} /></button></div></details> : null}
  </MainTag><footer className="site-footer"><div><span className="footer-brand"><Compass size={20} />CareCompass</span><p>{copy.footerSub}</p></div><p>{copy.footer}</p></footer><div className="sr-only" aria-live="polite" aria-atomic="true">{announcement}</div>
  {modal === 'location' ? <Modal title={copy.locationTitle} closeLabel={copy.close} onClose={() => setModal(null)}><p className="muted">{copy.locationBody}</p><div className="location-options">{locations.map(option => <button key={option.label} className={`location-option ${draftLocation.label === option.label ? 'chosen' : ''}`} aria-pressed={draftLocation.label === option.label} onClick={() => setDraftLocation(option)}><MapPin size={18} /><span>{option.lat === 0 ? copy.outside : option.label}</span>{draftLocation.label === option.label ? <Check size={18} /> : null}</button>)}</div><button className="button primary full-width" onClick={saveLocation}>{copy.saveLocation}<ArrowRight size={17} /></button></Modal> : null}
  {modal === 'help' ? <Modal title={copy.helpTitle} closeLabel={copy.close} onClose={() => setModal(null)}><div className="help-content"><p>{copy.helpBody}</p><h3>{copy.demo}</h3><p>{copy.helpData}</p><h3>{copy.speak}</h3><p>{copy.helpVoice}</p><h3>{copy.emergencyTitle}</h3><p>{copy.emergencyBody}</p><a className="text-button" href="https://112.gov.in/" target="_blank" rel="noreferrer">112 India <ArrowRight size={15} /></a></div></Modal> : null}
  {modal === 'how' ? <Modal title={copy.worksTitle} closeLabel={copy.close} onClose={() => setModal(null)}><div className="how-steps">{[{ title: copy.journeyDescribe, body: copy.worksIntake, Icon: MessageCircle }, { title: copy.journeyCare, body: copy.worksRoute, Icon: Stethoscope }, { title: copy.journeyBook, body: copy.worksMatch, Icon: ShieldCheck }].map(({ title, body, Icon }) => <section key={title}><Icon size={21} /><div><h3>{title}</h3><p>{body}</p></div></section>)}</div><p className="small muted">{copy.demoNotice}</p></Modal> : null}
  </>;
}
