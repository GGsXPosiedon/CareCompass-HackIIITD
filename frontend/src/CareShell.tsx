import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowUpRight, CalendarDays, ChevronRight, Globe2, HeartHandshake, Menu, MessageSquare, PanelLeftClose, PanelLeftOpen, Plus, X } from 'lucide-react';
import App from './App';
import { getCopy } from './i18n';
import type { Language } from './types';
const Portal = lazy(() => import('./health/Portal'));

export default function CareShell() {
  const [page, setPage] = useState<'care' | 'bookings' | 'workspace'>('care');
  const [language, setLanguage] = useState<Language>('en');
  const [resetKey, setResetKey] = useState(0);
  const [collapsed, setCollapsed] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [guide, setGuide] = useState(false);
  const [workspaceVisited, setWorkspaceVisited] = useState(false);
  const sidebar = useRef<HTMLElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const hi = language === 'hi';
  const copy = getCopy(hi);
  const t = (en: string, hindi: string) => hi ? hindi : en;
  function newRequest() { setPage('care'); setResetKey(n => n + 1); setDrawer(false); }
  function navigate(next: 'care' | 'bookings' | 'workspace') { if (next === 'workspace') setWorkspaceVisited(true); setPage(next); setDrawer(false); }
  useEffect(() => { document.documentElement.lang = hi ? 'hi' : 'en'; }, [hi, page]);
  useEffect(() => {
    if (!drawer) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const controls = () => Array.from(sidebar.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href]') ?? []).filter(el => el.getClientRects().length > 0);
    controls()[0]?.focus();
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') { event.preventDefault(); setDrawer(false); }
      if (event.key !== 'Tab') return;
      const targets = controls(); const first = targets[0]; const last = targets.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
    document.addEventListener('keydown', handleKey);
    return () => { document.body.style.overflow = previousOverflow; document.removeEventListener('keydown', handleKey); menuButton.current?.focus(); };
  }, [drawer]);

  return <div className={`care-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
    <a className="skip-link" href="#care-main">{copy.skip}</a>
    {drawer ? <button className="care-drawer-backdrop" tabIndex={-1} aria-label={copy.close} onClick={() => setDrawer(false)} /> : null}
    <aside ref={sidebar} role={drawer ? 'dialog' : undefined} aria-modal={drawer ? true : undefined} className={`care-sidebar ${drawer ? 'is-open' : ''}`} aria-label={t('Care navigation', 'देखभाल नेविगेशन')} inert={collapsed && !drawer}>
      <div className="care-sidebar-brand"><button onClick={newRequest} aria-label="CareCompass home"><img src="/compass.svg" width="27" height="27" alt=""/><span>CareCompass</span></button><button className="icon-button sidebar-desktop-toggle" aria-label={t('Collapse sidebar', 'साइडबार बंद करें')} onClick={() => setCollapsed(true)}><PanelLeftClose size={18}/></button><button className="icon-button sidebar-mobile-close" aria-label={copy.close} onClick={() => setDrawer(false)}><X size={20}/></button></div>
      <button className="care-new-request" onClick={newRequest}><Plus size={19}/>{t('New request', 'नई शुरुआत')}</button>
      <nav className="care-primary-nav" aria-label={t('Main navigation', 'मुख्य नेविगेशन')}>
        <button className={page === 'care' ? 'active' : ''} aria-current={page === 'care' ? 'page' : undefined} onClick={() => navigate('care')}><MessageSquare size={18}/>{copy.findCare}</button>
        <button className={page === 'bookings' ? 'active' : ''} aria-current={page === 'bookings' ? 'page' : undefined} onClick={() => navigate('bookings')}><CalendarDays size={18}/>{copy.bookings}</button>
      </nav>
      <div className="care-sidebar-help"><button className="care-guide-toggle" onClick={() => setGuide(!guide)} aria-expanded={guide}>{copy.howItWorks}<ChevronRight size={16} className={guide ? 'rotated' : ''}/></button>{guide ? <ol><li>{t('Describe the need.', 'ज़रूरत बताएँ।')}</li><li>{t('Answer a few questions.', 'कुछ सवालों के जवाब दें।')}</li><li>{t('Review the care recommendation.', 'देखभाल का सुझाव देखें।')}</li><li>{t('Choose a caregiver and time.', 'देखभालकर्ता और समय चुनें।')}</li><li>{t('Confirm a demo booking.', 'डेमो बुकिंग पक्की करें।')}</li></ol> : null}</div>
      <div className="care-sidebar-bottom"><button className="care-workspace-link" onClick={() => navigate('workspace')}><HeartHandshake size={18}/><span>{t('Family workspace', 'परिवार का कार्यस्थल')}<small>{t('Profiles, records & more', 'प्रोफ़ाइल, रिकॉर्ड और अधिक')}</small></span><ArrowUpRight size={16}/></button><div className="care-demo-note"><span/>{t('Demo · no real appointments', 'डेमो · कोई वास्तविक बुकिंग नहीं')}</div></div>
    </aside>
    <div className="care-stage" inert={drawer}>
      <header className="care-topbar"><div><button ref={menuButton} className="icon-button care-mobile-menu" aria-label={t('Open navigation', 'नेविगेशन खोलें')} aria-expanded={drawer} onClick={() => setDrawer(true)}><Menu size={21}/></button>{collapsed ? <button className="icon-button sidebar-desktop-toggle" aria-label={t('Expand sidebar', 'साइडबार खोलें')} onClick={() => setCollapsed(false)}><PanelLeftOpen size={20}/></button> : null}<span className="care-mobile-brand">CareCompass</span><span className="care-topbar-name">{page === 'bookings' ? copy.bookings : page === 'workspace' ? t('Family workspace', 'परिवार का कार्यस्थल') : copy.findCare}</span></div><div><span className="care-demo-badge">{t('Demo', 'डेमो')}</span><label className="language-control"><Globe2 size={16}/><select aria-label={copy.language} value={language} onChange={e => setLanguage(e.target.value as Language)}><option value="en">English</option><option value="hi">हिंदी</option><option value="hinglish">Hinglish</option><option value="auto">Auto</option></select></label></div></header>
      <div id="care-main" role={page === 'workspace' ? undefined : 'main'} className={page === 'workspace' ? 'care-main workspace-mode' : 'care-main'}>
        <div className="care-shell-flow" hidden={page === 'workspace'}><App embedded chatLayout externalLanguage={language} externalBookings={page === 'bookings'} resetRequest={resetKey} onStartCare={() => setPage('care')} onViewBookings={() => setPage('bookings')}/></div>
        {workspaceVisited ? <div className="care-legacy-workspace" hidden={page !== 'workspace'}><button className="care-workspace-back text-button" onClick={() => navigate('care')}><ArrowLeft size={17}/>{t('Back to finding care', 'देखभाल खोजने पर लौटें')}</button><Suspense fallback={<p className="workspace-loading" role="status">{t('Opening your family workspace…', 'परिवार का कार्यस्थल खोल रहे हैं…')}</p>}><Portal/></Suspense></div> : null}
      </div>
    </div>
  </div>;
}
