import { useEffect, useRef, useState } from 'react';
import { Download, Share, X } from 'lucide-react';
import { dismissInstall, installDismissed, installGuide, requestInstall } from '../lib/home-install';
import type { NativeInstallPrompt } from '../lib/home-install';
import './home-install.css';

export function HomeScreenInstall({ hindi, hidden }: { hindi: boolean; hidden: boolean }) {
  const [visible, setVisible] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [installed, setInstalled] = useState(false);
  const [nativeReady, setNativeReady] = useState(false);
  const [instructions, setInstructions] = useState(false);
  const [busy, setBusy] = useState(false);
  const deferred = useRef<NativeInstallPrompt | null>(null);
  const installing = useRef(false);
  const t = (en: string, hi: string) => hindi ? hi : en;
  const guide = installGuide(navigator.userAgent, navigator.maxTouchPoints);

  useEffect(() => {
    const narrow = matchMedia('(max-width: 767px)');
    const standalone = matchMedia('(display-mode: standalone)');
    const syncMobile = () => setMobile(narrow.matches);
    const syncInstalled = () => {
      const active = standalone.matches || !!(navigator as Navigator & { standalone?: boolean }).standalone;
      setInstalled(active);
      if (active) setVisible(false);
    };
    syncMobile(); syncInstalled();
    const timer = window.setTimeout(() => {
      let dismissed = false;
      try { dismissed = installDismissed(localStorage); } catch { /* Restricted storage. */ }
      if (!dismissed) setVisible(true);
    }, 3000);
    const ready = (event: Event) => {
      if (!narrow.matches) return;
      event.preventDefault();
      deferred.current = event as NativeInstallPrompt;
      setNativeReady(true);
    };
    const added = () => { deferred.current = null; setNativeReady(false); setInstalled(true); setVisible(false); };
    window.addEventListener('beforeinstallprompt', ready);
    window.addEventListener('appinstalled', added);
    narrow.addEventListener('change', syncMobile);
    standalone.addEventListener('change', syncInstalled);
    if (import.meta.env.PROD && window.isSecureContext && 'serviceWorker' in navigator) {
      void navigator.serviceWorker.register('/sw.js').catch(() => { /* Browser instructions remain available. */ });
    }
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('beforeinstallprompt', ready);
      window.removeEventListener('appinstalled', added);
      narrow.removeEventListener('change', syncMobile);
      standalone.removeEventListener('change', syncInstalled);
    };
  }, []);

  function dismiss() {
    setVisible(false);
    try { dismissInstall(localStorage); } catch { /* Restricted storage. */ }
  }
  async function add() {
    if (installing.current) return;
    const prompt = deferred.current;
    if (!prompt) { setInstructions(value => !value); return; }
    deferred.current = null; setNativeReady(false);
    installing.current = true; setBusy(true);
    try {
      const outcome = await requestInstall(prompt);
      if (outcome === 'accepted') setVisible(false);
      else dismiss();
    } catch { setInstructions(true); }
    finally { installing.current = false; setBusy(false); }
  }

  if (!visible || !mobile || installed || hidden) return null;
  return <aside className="home-install" aria-label={t('Add CareCompass to your home screen', 'CareCompass होम स्क्रीन पर जोड़ें')}>
    <div className="home-install-main">
      <img src="/icons/icon-192.png" width="40" height="40" alt=""/>
      <div aria-live="polite"><strong>{t('CareCompass, one tap away', 'CareCompass, बस एक टैप दूर')}</strong><p>{nativeReady ? t('Add an app icon to your phone’s home screen.', 'अपने फ़ोन की होम स्क्रीन पर ऐप आइकन जोड़ें।') : t('Keep a shortcut on your home screen for quick access.', 'जल्दी खोलने के लिए होम स्क्रीन पर शॉर्टकट रखें।')}</p></div>
      <button type="button" className="home-install-close" onClick={dismiss} aria-label={t('Dismiss installation notice', 'इंस्टॉल सूचना बंद करें')}><X size={18}/></button>
    </div>
    <button type="button" className="home-install-action" onClick={add} disabled={busy} aria-expanded={!nativeReady ? instructions : undefined}><Download size={16}/>{busy ? t('Opening installer…', 'इंस्टॉलर खुल रहा है…') : t('Add to home screen', 'होम स्क्रीन पर जोड़ें')}</button>
    {instructions ? <div className="home-install-steps" role="status">
      {guide === 'ios-browser' ? <p>{t('Open this page in Safari first.', 'पहले इस पेज को Safari में खोलें।')}</p> : null}
      {guide !== 'browser' ? <p><Share size={16}/>{t('Tap Share → Add to Home Screen → Add. Enable “Open as Web App” if shown.', 'Share → Add to Home Screen → Add चुनें। विकल्प दिखे तो “Open as Web App” चालू करें।')}</p> : <p>{t('Open your browser’s ⋮ menu → Install app or Add to Home screen → Install / Add. If you’re inside WhatsApp, open this page in Chrome first.', 'ब्राउज़र का ⋮ मेन्यू → Install app या Add to Home screen → Install / Add चुनें। WhatsApp के अंदर हों तो पहले Chrome में खोलें।')}</p>}
    </div> : null}
  </aside>;
}
