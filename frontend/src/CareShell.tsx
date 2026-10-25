import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import type { MouseEvent } from 'react';
import { ArrowLeft, BriefcaseMedical, CalendarDays, ChevronRight, Globe2, History, Menu, MessageSquare, PanelLeftClose, PanelLeftOpen, Plus, Settings as SettingsIcon, X } from 'lucide-react';
import App from './App';
import { getCopy } from './i18n';
import type { Language } from './types';
import { HealthProvider } from './health/Store';
import { VoiceLanguageContext } from './voice/language';
import { stopAllVoice } from './voice/client';
import { ChatHistory } from './components/ChatHistory';
import { HISTORY_KEY, readHistory, saveConversation } from './lib/history';
import { ConversationSidebar } from './components/ConversationSidebar';
import { Settings } from './components/Settings';
import type { CareConversation } from './lib/history';
const Briefcase = lazy(() => import('./health/Briefcase'));
const Services = lazy(() => import('./health/Services').then(module => ({ default: module.Services })));
import { conversationPath, pagePaths, parentPath, resolveRoute } from './lib/routes';
import type { Page } from './lib/routes';

function Shell() {
  const [pathname, setPathname] = useState(window.location.pathname);
  const navigationTrail = useRef<string[]>([]);
  const route = resolveRoute(pathname);
  const page = route.page;
  const [history, setHistory] = useState<CareConversation[]>(() => { try { return readHistory(window.localStorage); } catch { return []; } });
  const [activeId, setActiveId] = useState<string | null>(null);
  const [storageError, setStorageError] = useState(false);
  const [restoredConversation, setRestoredConversation] = useState<{ entry: CareConversation }>();
  const [language, setLanguage] = useState<Language>('auto');
  const [theme, setTheme] = useState<'dark' | 'light'>(() => { try { return localStorage.getItem('carecompass.theme') === 'dark' ? 'dark' : 'light'; } catch { return 'light'; } });
  const [resetKey, setResetKey] = useState(0);
  const [collapsed, setCollapsed] = useState(() => { try { return localStorage.getItem('carecompass.sidebarCollapsed') === 'true'; } catch { return false; } });
  const [drawer, setDrawer] = useState(false);
  const [guide, setGuide] = useState(false);
  const [briefcaseVisited, setBriefcaseVisited] = useState(false);
  const [servicesVisited, setServicesVisited] = useState(false);
  const sidebar = useRef<HTMLElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const hi = language === 'hi';
  const copy = getCopy(hi);
  const t = (en: string, hindi: string) => hi ? hindi : en;
  function newRequest() { setActiveId(null); setRestoredConversation(undefined); changeRoute(pagePaths.care); setResetKey(n => n + 1); setDrawer(false); }
  function openConversation(entry: CareConversation) { setActiveId(entry.id); setLanguage(entry.language); setRestoredConversation({ entry }); changeRoute(conversationPath(entry.id)); }
  function deleteConversation(id: string) { setHistory(previous => previous.filter(entry => entry.id !== id)); if (activeId === id) newRequest(); }
  useEffect(() => {
    try { window.localStorage.setItem(HISTORY_KEY, JSON.stringify(history)); setStorageError(false); }
    catch { setStorageError(true); }
  }, [history]);
  function changeRoute(path: string, replace = false) {
    if (window.location.pathname !== path) {
      if (replace) window.history.replaceState(null, '', path);
      else { navigationTrail.current.push(window.location.pathname); window.history.pushState(null, '', path); }
    }
    setPathname(path); setDrawer(false); window.scrollTo({ top:0, behavior:'instant' });
  }
  function goBack() {
    if (navigationTrail.current.length) window.history.back();
    else changeRoute(parentPath(pathname, activeId), true);
  }
  function followLink(event: MouseEvent<HTMLAnchorElement>, next: Page) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault(); navigate(next);
  }
  function navigate(next: Page) { changeRoute(next === 'care' && activeId ? conversationPath(activeId) : pagePaths[next]); }
  useEffect(() => {
    if (window.location.pathname === '/') { window.history.replaceState(null, '', pagePaths.care); setPathname(pagePaths.care); }
    const pop = () => { navigationTrail.current.pop(); setPathname(window.location.pathname); setDrawer(false); window.scrollTo({ top:0, behavior:'instant' }); };
    window.addEventListener('popstate', pop);
    return () => window.removeEventListener('popstate', pop);
  }, []);
  useEffect(() => {
    if (page === 'briefcase') setBriefcaseVisited(true);
    if (page === 'services') setServicesVisited(true);
    if (page !== 'care') return;
    if (route.conversationId) {
      const entry = history.find(item => item.id === route.conversationId);
      if (entry && activeId !== entry.id) { setActiveId(entry.id); setLanguage(entry.language); setRestoredConversation({ entry }); }
    } else if (activeId) {
      setActiveId(null); setRestoredConversation(undefined); setResetKey(n => n + 1);
    }
  }, [pathname, history, activeId]);
  useEffect(() => { document.documentElement.lang = hi ? 'hi' : 'en'; }, [hi, page]);
  useEffect(() => { stopAllVoice(); }, [page, resetKey, language, drawer]);
  useEffect(() => {
    const pause = () => { if (document.hidden) stopAllVoice(); };
    document.addEventListener('visibilitychange', pause);
    return () => { document.removeEventListener('visibilitychange', pause); stopAllVoice(); };
  }, []);
  useEffect(() => {
    document.documentElement.dataset.careMotion = 'full';
    return () => { delete document.documentElement.dataset.careMotion; };
  }, []);
  useEffect(() => {
    document.documentElement.style.colorScheme = theme;
    try { localStorage.setItem('carecompass.theme', theme); } catch { /* In-memory preference still works. */ }
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#20201e' : '#faf9f6');
  }, [theme]);
  useEffect(() => {
    try { localStorage.setItem('carecompass.sidebarCollapsed', String(collapsed)); } catch { /* In-memory preference still works. */ }
  }, [collapsed]);
  useEffect(() => {
    const mobile = window.matchMedia('(max-width: 767px)');
    const sync = () => { if (!mobile.matches) setDrawer(false); };
    mobile.addEventListener('change', sync);
    return () => mobile.removeEventListener('change', sync);
  }, []);
  useEffect(() => {
    if (!drawer) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const controls = () => Array.from(sidebar.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled)') ?? []).filter(el => el.getClientRects().length > 0);
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

  return <VoiceLanguageContext.Provider value={language}><div className={`care-shell theme-${theme} ${collapsed ? 'sidebar-collapsed' : ''}`}>
    <a className="skip-link" href="#care-main">{copy.skip}</a>
    {drawer ? <button className="care-drawer-backdrop" tabIndex={-1} aria-label={copy.close} onClick={() => setDrawer(false)} /> : null}
    <aside ref={sidebar} role={drawer ? 'dialog' : undefined} aria-modal={drawer ? true : undefined} className={`care-sidebar ${drawer ? 'is-open' : ''}`} aria-label={t('Care navigation', 'देखभाल नेविगेशन')}>
      <div className="care-sidebar-brand"><button onClick={newRequest} aria-label="CareCompass home"><img src="/compass.svg" width="27" height="27" alt=""/><span>CareCompass</span></button><button className="icon-button sidebar-desktop-toggle" aria-label={collapsed ? t('Expand sidebar', 'साइडबार खोलें') : t('Collapse sidebar', 'साइडबार बंद करें')} aria-expanded={!collapsed} onClick={() => setCollapsed(value => !value)}>{collapsed ? <PanelLeftOpen size={18}/> : <PanelLeftClose size={18}/>}</button><button className="icon-button sidebar-mobile-close" aria-label={copy.close} onClick={() => setDrawer(false)}><X size={20}/></button></div>
      <button className="care-new-request" onClick={newRequest} aria-label={t('New request', 'नई शुरुआत')} title={t('New request', 'नई शुरुआत')}><Plus size={19}/><span className="sidebar-label">{t('New request', 'नई शुरुआत')}</span></button>
      <nav className="care-primary-nav" aria-label={t('Main navigation', 'मुख्य नेविगेशन')}>
        <a className={page === 'care' ? 'active' : ''} aria-current={page === 'care' ? 'page' : undefined} href={activeId ? conversationPath(activeId) : pagePaths.care} aria-label={copy.findCare} title={copy.findCare} onClick={event => followLink(event, 'care')}><MessageSquare size={18}/><span className="sidebar-label">{copy.findCare}</span></a>
        <a className={page === 'bookings' || page === 'services' ? 'active' : ''} aria-current={page === 'bookings' || page === 'services' ? 'page' : undefined} href={pagePaths.bookings} aria-label={copy.bookings} title={copy.bookings} onClick={event => followLink(event, 'bookings')}><CalendarDays size={18}/><span className="sidebar-label">{copy.bookings}</span></a>
        <a className={page === 'briefcase' ? 'active' : ''} aria-current={page === 'briefcase' ? 'page' : undefined} href={pagePaths.briefcase} aria-label={t('Briefcase', 'ब्रीफ़केस')} title={t('Briefcase', 'ब्रीफ़केस')} onClick={event => followLink(event, 'briefcase')}><BriefcaseMedical size={18}/><span className="sidebar-label">{t('Briefcase', 'ब्रीफ़केस')}</span></a>

        <a className={page === 'history' ? 'active' : ''} aria-current={page === 'history' ? 'page' : undefined} href={pagePaths.history} aria-label={t('Chat history', 'बातचीत का इतिहास')} title={t('Chat history', 'बातचीत का इतिहास')} onClick={event => followLink(event, 'history')}><History size={18}/><span className="sidebar-label">{t('Chat history', 'बातचीत का इतिहास')}</span></a>
      </nav>
      <ConversationSidebar history={history} activeId={activeId} hindi={hi} onOpen={openConversation} onRename={(id, title) => setHistory(previous => previous.map(entry => entry.id === id ? { ...entry, title, customTitle: title } : entry))} onDelete={deleteConversation}/>
      {storageError ? <p className="sidebar-history-note" role="status">{t('Storage is unavailable or full. Chats are kept in this tab only.', 'स्टोरेज उपलब्ध नहीं या भरा हुआ है। चैट सिर्फ़ इस टैब में हैं।')}</p> : null}
      <div className="care-sidebar-help"><button className="care-guide-toggle" onClick={() => setGuide(!guide)} aria-expanded={guide}>{copy.howItWorks}<ChevronRight size={16} className={guide ? 'rotated' : ''}/></button>{guide ? <ol><li>{t('Describe the need.', 'ज़रूरत बताएँ।')}</li><li>{t('Answer a few questions.', 'कुछ सवालों के जवाब दें।')}</li><li>{t('Review the care recommendation.', 'देखभाल का सुझाव देखें।')}</li><li>{t('Choose a caregiver and time.', 'देखभालकर्ता और समय चुनें।')}</li><li>{t('Confirm a demo booking.', 'डेमो बुकिंग पक्की करें।')}</li></ol> : null}</div>
      <div className="care-sidebar-bottom"><a className={`care-settings-link ${page === 'settings' ? 'active' : ''}`} href={pagePaths.settings} onClick={event => followLink(event, 'settings')} aria-label={t('Settings', 'सेटिंग्स')} title={t('Settings', 'सेटिंग्स')} aria-current={page === 'settings' ? 'page' : undefined}><SettingsIcon size={18}/><span className="sidebar-label">{t('Settings', 'सेटिंग्स')}</span></a><div className="care-demo-note"><span/>{t('Demo · no real appointments', 'डेमो · कोई वास्तविक बुकिंग नहीं')}</div></div>
    </aside>
    <div className="care-stage" inert={drawer}>
      <header className="care-topbar"><div>{page !== 'care' ? <button type="button" className="care-back-button" onClick={goBack} aria-label={t('Go back', 'वापस जाएँ')}><ArrowLeft size={17}/><span>{t('Back', 'वापस')}</span></button> : null}<button ref={menuButton} className="icon-button care-mobile-menu" aria-label={t('Open navigation', 'नेविगेशन खोलें')} aria-expanded={drawer} onClick={() => setDrawer(true)}><Menu size={21}/></button><span className="care-mobile-brand">CareCompass</span><span className="care-topbar-name">{page === 'bookings' ? copy.bookings : page === 'briefcase' ? t('Briefcase', 'ब्रीफ़केस') : page === 'services' ? t('Health services', 'स्वास्थ्य सेवाएँ') : page === 'history' ? t('Chat history', 'बातचीत का इतिहास') : page === 'settings' ? t('Settings', 'सेटिंग्स') : copy.findCare}</span></div><div><span className="care-demo-badge">{t('Demo', 'डेमो')}</span><label className="language-control"><Globe2 size={16}/><select aria-label={copy.language} value={language} onChange={e => setLanguage(e.target.value as Language)}><option value="en">English</option><option value="hi">हिंदी</option><option value="hinglish">Hinglish</option><option value="auto">Auto</option></select></label></div></header>
      <div id="care-main" role="main" className="care-main">
        {page === 'not-found' || (route.conversationId && !history.some(entry => entry.id === route.conversationId)) ? <section className="care-route-missing"><h1>{t('Page not found', 'पेज नहीं मिला')}</h1><p>{t('This page or saved conversation is unavailable on this device.', 'यह पेज या सहेजी गई बातचीत इस डिवाइस पर उपलब्ध नहीं है।')}</p><button className="button primary" onClick={newRequest}>{t('Start a new conversation', 'नई बातचीत शुरू करें')}</button></section> : null}
        <div className="care-shell-flow" hidden={(page !== 'care' && page !== 'bookings') || !!(route.conversationId && !history.some(entry => entry.id === route.conversationId))}><App active={page === 'care'} embedded chatLayout restoredConversation={restoredConversation} onConversation={entry => { setActiveId(entry.id); setHistory(previous => saveConversation(previous, entry)); if (window.location.pathname !== conversationPath(entry.id)) changeRoute(conversationPath(entry.id)); }} externalLanguage={language} externalBookings={page === 'bookings'} resetRequest={resetKey} onStartCare={() => navigate('care')} onViewBookings={() => navigate('bookings')} onExploreServices={() => navigate('services')}/></div>
        {page === 'settings' ? <Settings hindi={hi} theme={theme} onTheme={setTheme}/> : null}
        {page === 'history' ? <ChatHistory history={history} hindi={hi} onNew={newRequest} onOpen={openConversation} onRename={(id, title) => setHistory(previous => previous.map(entry => entry.id === id ? { ...entry, title, customTitle: title } : entry))} onDelete={deleteConversation}/> : null}
        {briefcaseVisited || page === 'briefcase' ? <div className="care-support-page" hidden={page !== 'briefcase'}><Suspense fallback={<p className="workspace-loading" role="status">{t('Opening your briefcase…', 'ब्रीफ़केस खोल रहे हैं…')}</p>}><Briefcase hi={hi}/></Suspense></div> : null}
        {servicesVisited || page === 'services' ? <div className="care-support-page" hidden={page !== 'services'}><div className="health-portal services-content"><Suspense fallback={<p role="status">{t('Opening health services…', 'स्वास्थ्य सेवाएँ खोल रहे हैं…')}</p>}><Services hi={hi} onCare={newRequest}/></Suspense></div></div> : null}
      </div>
    </div>
  </div></VoiceLanguageContext.Provider>;
}

export default function CareShell(){return <HealthProvider><Shell/></HealthProvider>;}
