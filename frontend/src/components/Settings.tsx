import { ArrowRight, Moon, Sun, UserRound } from 'lucide-react';

export function Settings({ hindi, theme, onTheme, onProfile }: {
  hindi: boolean; theme: 'light' | 'dark'; onTheme: (theme: 'light' | 'dark') => void; onProfile: () => void;
}) {
  const t = (en: string, hi: string) => hindi ? hi : en;
  return <section className="care-settings" aria-labelledby="settings-title">
    <div className="page-heading"><h1 id="settings-title">{t('Settings', 'सेटिंग्स')}</h1><p>{t('Your profile and preferences, in one place.', 'आपकी प्रोफ़ाइल और पसंद, एक जगह।')}</p></div>
    <section className="settings-section" aria-labelledby="settings-profile"><h2 id="settings-profile">{t('Profile & family', 'प्रोफ़ाइल और परिवार')}</h2>
      <button className="settings-profile-link" onClick={onProfile}><UserRound size={20}/><span><strong>{t('Manage profiles', 'प्रोफ़ाइल सँभालें')}</strong><small>{t('Family members, health details and assistant access.', 'परिवार के सदस्य, स्वास्थ्य जानकारी और असिस्टेंट की पहुँच।')}</small></span><ArrowRight size={17}/></button>
    </section>
    <section className="settings-section" aria-labelledby="settings-appearance"><h2 id="settings-appearance">{t('Appearance', 'दिखावट')}</h2><p>{t('Choose the theme that feels right for you.', 'अपनी पसंद की थीम चुनें।')}</p>
      <div className="settings-theme-options" role="group" aria-label={t('Color theme', 'रंग थीम')}>
        <button className={theme === 'light' ? 'selected' : ''} aria-pressed={theme === 'light'} onClick={() => onTheme('light')}><Sun size={19}/>{t('Light', 'लाइट')}</button>
        <button className={theme === 'dark' ? 'selected' : ''} aria-pressed={theme === 'dark'} onClick={() => onTheme('dark')}><Moon size={19}/>{t('Dark', 'डार्क')}</button>
      </div>
    </section>
  </section>;
}
