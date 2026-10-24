import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, ChevronDown, Compass, Globe2, HelpCircle, MapPin, Menu, MessageCircle, ShieldCheck, Stethoscope, X } from 'lucide-react';
import { careLabel, getCopy } from './i18n';
import { emergencyExample, locations, scenarios } from './data';
import { createBooking, DEMO_MODE, getCaregivers, intake } from './lib/api';
import { bookingSlots, bookingDate, nextView } from './lib/flow';
import { ApiError } from './lib/http';
import type { PatientContext, Booking, Caregiver, IntakeRequest, Language, Location, Message, TriageResponse } from './types';
import { Intake } from './components/Intake';
import { FollowUps } from './components/FollowUps';
import { ChatQuestion } from './components/ChatQuestion';
import { Recommendation } from './components/Recommendation';
import { Caregivers } from './components/Caregivers';
import { BookingForm, Bookings, Confirmation } from './components/Booking';
import { Emergency } from './components/Emergency';
import { Modal } from './components/Modal';
import { VoiceResponseContext, VoiceConversationContext, VoiceSessionActiveContext, VoiceComposerHostContext } from './voice/language';
import { primeVoicePlayback, suppressResponseVoice } from './voice/playback';
import { stopAllVoice } from './voice/client';
import { VoiceConversation } from './components/VoiceConversation';
import type { SpokenReply } from './voice/conversation';
import { VoiceComposerSlot } from './components/VoiceComposerSlot';
import type { CareConversation } from './lib/history';

type View = 'intake' | 'questions' | 'recommendation' | 'caregivers' | 'booking' | 'confirmation' | 'bookings' | 'emergency';
type ModalView = 'location' | 'help' | 'how' | null;
export default function App({ embedded = false, chatLayout = false, resetRequest = 0, externalLanguage, patientName, patientContext, externalBookings, restoredConversation, onConversation, onStartCare, onViewBookings, onExploreServices }: { embedded?: boolean; chatLayout?: boolean; resetRequest?: number; externalLanguage?: Language; patientName?: string; patientContext?: PatientContext; externalBookings?: boolean; restoredConversation?: { entry: CareConversation }; onConversation?: (entry: CareConversation) => void; onStartCare?: () => void; onViewBookings?: () => void; onExploreServices?: () => void }) {
  const [view, setView] = useState<View>('intake');
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [voiceHost, setVoiceHost] = useState<HTMLDivElement | null>(null);
  const conversationId = useRef<string | null>(null);
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
  const [date, setDate] = useState(bookingDate());
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
  useEffect(() => { if (resetRequest) reset(); }, [resetRequest]);
  useEffect(() => {
    if (externalBookings) { generation.current++; locked.current = false; setBusy(false); setError(''); setView('bookings'); }
    else if (embedded && view === 'bookings') setView('intake');
  }, [externalBookings]);
  useEffect(() => {
    if (!restoredConversation) return;
    const entry = restoredConversation.entry;
    stopAllVoice(); generation.current++; locked.current = false; conversationId.current = entry.id;
    suppressResponseVoice(entry.result);
    setVoiceOpen(false); setBusy(false); setError(''); setLanguage(entry.language); setInput(entry.input); setPerson(entry.person);
    setLocation(entry.location); setMessages(entry.messages); setResult(entry.result); setAnswer('');
    setProfiles([]); setSelected(null); setSlot(''); setView(nextView(entry.result));
  }, [restoredConversation]);
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
    if (view !== 'intake') main.current?.querySelector<HTMLElement>('h1')?.focus({ preventScroll: true });
  }, [view]);
  useEffect(() => {
    if (view === 'questions' && result?.follow_up_question) setAnnouncement(result.follow_up_question);
  }, [result, view]);

  function reset() {
    conversationId.current = null;
    setVoiceOpen(false);
    generation.current++; locked.current = false;
    setBusy(false); setView('intake'); setInput(''); setAnswer(''); setMessages([]); setResult(null); setProfiles([]); setSelected(null); setSlot(''); setError(''); setFilter('all'); setMenu(false); setAnnouncement('');
    onStartCare?.();
  }
  function edit() {
    conversationId.current = null;
    setVoiceOpen(false);
    generation.current++; locked.current = false;
    setBusy(false); setView('intake'); setAnswer(''); setMessages([]); setResult(null); setProfiles([]); setSelected(null); setError(''); setSlot('');
  }
  function updateLanguage(value: Language) {
    setLanguage(value);
    // A response's language belongs to its request; restart unfinished intake when switching.
    if (messages.length && view !== 'confirmation' && view !== 'bookings') edit();
    setError('');
  }
  async function submit(override?: { text: string; location?: Location; simulateError?: boolean; answer?: boolean; voice?: boolean }) {
    if (locked.current) return;
    const followUp = view === 'questions' && (!override || !!override.answer);
    const text = (override?.text ?? (followUp ? answer : input)).trim();
    if (!text) { setError(copy.blank); return; }
    if (text.length > 2000) { setError(copy.tooLong); return; }
    if (!override?.voice) stopAllVoice();
    primeVoicePlayback(); // Unlock audio in the send gesture before awaiting the API.
    const history = followUp ? messages : [];
    const requestLocation = override?.location ?? location;
    const relation = `${patientName ? `${patientName} (demo) · ` : ''}${person === 'me' ? copy.me : copy.family}`;
    const payload: IntakeRequest = { user_input: followUp || chatLayout ? text : `${relation}: ${text}`, language: language === 'en' ? 'auto' : language, location: { lat: requestLocation.lat, lng: requestLocation.lng }, conversation_history: history, ...(patientContext ? { patient_context: patientContext } : {}) };
    const current = ++generation.current; locked.current = true; setBusy(true); setError('');
    if (!followUp) { setInput(text); setLocation(requestLocation); setMessages([]); setResult(null); setSelected(null); setProfiles([]); setView('intake'); }
    try {
      if (override?.simulateError) throw new Error('DEMO_ERROR');
      const response = await intake(payload);
      if (current !== generation.current) return;
      if (override?.voice) suppressResponseVoice(response); // Ending voice mode also silences a late care reply.
      const nextMessages: Message[] = [...history, { role: 'user', content: payload.user_input }];
      if (response.follow_up_question) nextMessages.push({ role: 'assistant', content: response.follow_up_question });
      setMessages(nextMessages); setResult(response); setAnswer(''); setView(nextView(response));
      if (!followUp || !conversationId.current) conversationId.current = crypto.randomUUID();
      const archivedMessages: Message[] = response.follow_up_question ? nextMessages : [...nextMessages, { role: 'assistant', content: nextView(response) === 'emergency' ? `${copy.emergencyTitle} ${response.reasoning} ${copy.emergencyBody}` : `${careLabel(response.care_type!, hindi)}. ${response.reasoning}` }];
      onConversation?.({ id: conversationId.current, title: (followUp ? input : text).slice(0, 100), input: followUp ? input : text, person, language, location: requestLocation, messages: archivedMessages, result: response, updatedAt: new Date().toISOString() });
      return response;
    } catch (cause) { if (current === generation.current) setError(!DEMO_MODE && (cause instanceof TypeError || cause instanceof DOMException || (cause instanceof ApiError && cause.status >= 500)) ? copy.connectionError : copy.genericError); }
    finally { if (current === generation.current) { setBusy(false); locked.current = false; } }
  }
  async function fetchProfiles(on: string): Promise<Caregiver[]> {
    if (!result?.matched_caregivers.length) return [];
    const data = await getCaregivers(result.matched_caregivers.map(m => m.caregiver_id), { careType: result.care_type, lat: location.lat, lng: location.lng, date: on });
    const ranked = result.matched_caregivers.map(m => data.find(c => c.id === m.caregiver_id));
    if (ranked.some(c => !c || c.careType !== result.care_type)) throw new Error('MISSING_PROFILE');
    return ranked as Caregiver[];
  }
  async function refreshProfiles(on: string, target: 'caregivers' | 'booking', preserveSelection = true, notice = '') {
    if (!result || locked.current) return;
    const selectedId = preserveSelection ? selected?.id : undefined;
    const current = ++generation.current; locked.current = true;
    setBusy(true); setError(''); setDate(on); setSlot(''); setProfiles([]); setView(target);
    setSelected(previous => preserveSelection && previous ? { ...previous, slots: [] } : null);
    if (!preserveSelection) setFilter('all');
    try {
      const ranked = await fetchProfiles(on);
      if (current !== generation.current) return;
      const next = ranked.find(c => c.id === selectedId);
      setProfiles(ranked);
      setSelected(next && (target === 'booking' || bookingSlots(next.slots, on).length) ? next : null);
      setError(notice);
    } catch { if (current === generation.current) setError(copy.profileError); }
    finally { if (current === generation.current) { setBusy(false); locked.current = false; } }
  }
  function loadProfiles() {
    void refreshProfiles(bookingDate(result?.urgency === 'scheduled' ? 1 : 0), 'caregivers', false);
  }
  async function confirm() {
    if (!selected || !result?.care_type || locked.current) return;
    if (!slot) { setError(copy.chooseSlot); return; }
    if (!bookingSlots(selected.slots, date).includes(slot)) { void refreshProfiles(date, 'booking', true, copy.slotTaken); return; }
    const current = ++generation.current; locked.current = true; setBusy(true); setError('');
    try {
      const response = await createBooking({ caregiver_id: selected.id, slot, date, location: { lat: location.lat, lng: location.lng } });
      if (current !== generation.current) return;
      const booking: Booking = { id: response.id, caregiver: selected, date, slot, location, careType: result.care_type, demo: DEMO_MODE };
      setBookings(previous => [booking, ...previous]); setConfirmed(booking); setView('confirmation');
    } catch (cause) {
      if (current !== generation.current) return;
      if (cause instanceof ApiError && cause.status === 409) {
        setSlot(''); setSelected(previous => previous ? { ...previous, slots: [] } : null); setProfiles([]);
        setError(copy.slotTaken);
        try {
          const ranked = await fetchProfiles(date);
          if (current !== generation.current) return;
          setProfiles(ranked); setSelected(ranked.find(c => c.id === selected.id) ?? { ...selected, slots: [] });
        } catch { if (current === generation.current) setError(`${copy.slotTaken} ${copy.profileError}`); }
      } else setError(copy.genericError);
    }
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
  <VoiceComposerHostContext.Provider value={setVoiceHost}><VoiceSessionActiveContext.Provider value={voiceOpen}><VoiceConversationContext.Provider value={() => { stopAllVoice(); primeVoicePlayback(); setVoiceOpen(true); }}><VoiceResponseContext.Provider value={result}><MainTag id={embedded ? undefined : 'main'} className={`main-container${chatLayout ? ` focused-care focused-${view}` : ''}`} ref={main}>
    <div className="context-bar">{displayProgress ? <ol className="progress" aria-label={hindi ? 'देखभाल की प्रगति' : 'Care progress'}>{[copy.describe, copy.recommendation, copy.book].map((step, index) => <li key={index} className={index === progress ? 'current' : index < progress ? 'complete' : ''} aria-current={index === progress ? 'step' : undefined}><span className="progress-mark">{index < progress ? <Check size={12} /> : <span />}</span>{step}{index < 2 ? <span className="progress-line" aria-hidden="true" /> : null}</li>)}</ol> : <span />}{DEMO_MODE ? <span className="demo-label"><span />{copy.demo}</span> : null}</div>
    {view === 'intake' ? <Intake compact={chatLayout} onLocation={showLocation} copy={copy} hindi={hindi} language={language} input={input} setInput={value => { setInput(value); setError(''); }} person={person} setPerson={setPerson} location={location} busy={busy} error={error} onSubmit={() => void submit()} /> : null}
    {view === 'questions' && result && chatLayout ? <ChatQuestion copy={copy} hindi={hindi} result={result} messages={messages} symptom={input} input={answer} setInput={value => { setAnswer(value); setError(''); }} onAnswer={text => void submit({ text, answer: true })} onBack={edit} busy={busy} error={error} /> : null}
    {view === 'questions' && result && !chatLayout ? <FollowUps copy={copy} hindi={hindi} result={result} messages={messages} input={answer} setInput={value => { setAnswer(value); setError(''); }} onSubmit={() => void submit()} onBack={edit} busy={busy} error={error} symptom={input} location={location} /> : null}
    {view === 'recommendation' && result ? <Recommendation copy={copy} hindi={hindi} result={result} symptom={input} location={location} answers={Math.max(0, messages.filter(m => m.role === 'user').length - 1)} busy={busy} error={error} onContinue={loadProfiles} onBack={edit} onLocation={showLocation} /> : null}
    {view === 'caregivers' && result ? <Caregivers copy={copy} hindi={hindi} profiles={profiles} result={result} selected={selected} setSelected={setSelected} filter={filter} setFilter={value => { setFilter(value); if (selected && value !== 'all' && !selected.languages.includes(value)) setSelected(null); }} location={location} date={date} busy={busy} error={error} onDateChange={on => void refreshProfiles(on, 'caregivers')} onRetry={() => void refreshProfiles(date, 'caregivers')} onBack={() => setView('recommendation')} onContinue={() => { if (selected) void refreshProfiles(date, 'booking'); }} /> : null}
    {view === 'booking' && selected && result?.care_type ? <BookingForm copy={copy} hindi={hindi} caregiver={selected} careType={result.care_type} location={location} date={date} setDate={on => void refreshProfiles(on, 'booking')} slot={slot} setSlot={value => { setSlot(value); setError(''); }} sameDay={result.urgency === 'same_day'} busy={busy} error={error} onBack={() => { setError(''); setView('caregivers'); }} onRetry={() => void refreshProfiles(date, 'booking')} onConfirm={() => void confirm()} /> : null}
    {view === 'confirmation' && confirmed ? <Confirmation copy={copy} hindi={hindi} booking={confirmed} onBookings={showBookings} onNew={reset} /> : null}
    {view === 'bookings' ? <Bookings copy={copy} hindi={hindi} bookings={bookings} onNew={reset} onExploreServices={onExploreServices} /> : null}
    {view === 'emergency' && result ? <Emergency copy={copy} hindi={hindi} result={result} onNew={reset} /> : null}
    {DEMO_MODE ? <details className="demo-tools"><summary>{copy.demoTools}</summary><p className="small muted">{copy.demoToolsNote}</p><div><button className="text-button" disabled={busy} onClick={() => void submit({ text: hindi ? emergencyExample.hi : emergencyExample.en })}>{copy.emergencyExample}<ArrowRight size={15} /></button><button className="text-button" disabled={busy} onClick={() => void submit({ text: hindi ? scenarios[0].textHi : scenarios[0].text, location: locations[3] })}>{copy.emptyExample}<ArrowRight size={15} /></button><button className="text-button" disabled={busy} onClick={() => void submit({ text: hindi ? scenarios[0].textHi : scenarios[0].text, simulateError: true })}>{copy.errorExample}<ArrowRight size={15} /></button></div></details> : null}
  {voiceOpen && (!chatLayout || (view !== 'intake' && view !== 'questions')) ? <div className="care-chat-composer voice-followup-composer"><VoiceComposerSlot/></div> : null}
  </MainTag></VoiceResponseContext.Provider>
  {voiceOpen ? <VoiceConversation copy={copy} language={language} host={voiceHost} onClose={() => setVoiceOpen(false)} onTurn={async text => {
    const response = await submit({ text, answer: view === 'questions', voice: true });
    if (!response) throw new Error('CARE_RESPONSE_UNAVAILABLE');
    const destination = nextView(response);
    const reply: SpokenReply = destination === 'emergency' ? { text: `${copy.emergencyTitle} ${response.reasoning} ${copy.emergencyBody}`, terminal: true }
      : destination === 'questions' ? { text: `${response.follow_up_question} ${response.answer_options?.join('. ') ?? ''}` }
      : { text: `${careLabel(response.care_type!, hindi)}. ${response.reasoning} ${copy.voiceSessionNext}` };
    return reply;
  }}/> : null}
  </VoiceConversationContext.Provider></VoiceSessionActiveContext.Provider></VoiceComposerHostContext.Provider><footer className="site-footer"><div><span className="footer-brand"><Compass size={20} />CareCompass</span><p>{copy.footerSub}</p></div><p>{copy.footer}</p></footer><div className="sr-only" aria-live="polite" aria-atomic="true">{announcement}</div>
  {modal === 'location' ? <Modal title={copy.locationTitle} closeLabel={copy.close} onClose={() => setModal(null)}><p className="muted">{copy.locationBody}</p><div className="location-options">{locations.map(option => <button key={option.label} className={`location-option ${draftLocation.label === option.label ? 'chosen' : ''}`} aria-pressed={draftLocation.label === option.label} onClick={() => setDraftLocation(option)}><MapPin size={18} /><span>{option.lat === 0 ? copy.outside : option.label}</span>{draftLocation.label === option.label ? <Check size={18} /> : null}</button>)}</div><button className="button primary full-width" onClick={saveLocation}>{copy.saveLocation}<ArrowRight size={17} /></button></Modal> : null}
  {modal === 'help' ? <Modal title={copy.helpTitle} closeLabel={copy.close} onClose={() => setModal(null)}><div className="help-content"><p>{copy.helpBody}</p><h3>{copy.demo}</h3><p>{copy.helpData}</p><h3>{copy.speak}</h3><p>{copy.helpVoice}</p><h3>{copy.emergencyTitle}</h3><p>{copy.emergencyBody}</p><a className="text-button" href="https://112.gov.in/" target="_blank" rel="noreferrer">112 India <ArrowRight size={15} /></a></div></Modal> : null}
  {modal === 'how' ? <Modal title={copy.worksTitle} closeLabel={copy.close} onClose={() => setModal(null)}><div className="how-steps">{[{ title: copy.journeyDescribe, body: copy.worksIntake, Icon: MessageCircle }, { title: copy.journeyCare, body: copy.worksRoute, Icon: Stethoscope }, { title: copy.journeyBook, body: copy.worksMatch, Icon: ShieldCheck }].map(({ title, body, Icon }) => <section key={title}><Icon size={21} /><div><h3>{title}</h3><p>{body}</p></div></section>)}</div><p className="small muted">{copy.demoNotice}</p></Modal> : null}
  </>;
}
