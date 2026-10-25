import { Moon, Sun } from 'lucide-react';

export function Settings({ hindi, theme, onTheme }: {
  hindi: boolean; theme: 'light' | 'dark'; onTheme: (theme: 'light' | 'dark') => void;
}) {
  const t = (en: string, hi: string) => hindi ? hi : en;
  return <section className="care-settings" aria-labelledby="settings-title">
    <div className="page-heading"><h1 id="settings-title">{t('Settings', 'सेटिंग्स')}</h1><p>{t('Your preferences, in one place.', 'आपकी पसंद, एक जगह।')}</p></div>
    <section className="settings-section" aria-labelledby="settings-appearance"><h2 id="settings-appearance">{t('Appearance', 'दिखावट')}</h2><p>{t('Choose the theme that feels right for you.', 'अपनी पसंद की थीम चुनें।')}</p>
      <div className="settings-theme-options" role="group" aria-label={t('Color theme', 'रंग थीम')}>
        <button className={theme === 'light' ? 'selected' : ''} aria-pressed={theme === 'light'} onClick={() => onTheme('light')}><Sun size={19}/>{t('Light', 'लाइट')}</button>
        <button className={theme === 'dark' ? 'selected' : ''} aria-pressed={theme === 'dark'} onClick={() => onTheme('dark')}><Moon size={19}/>{t('Dark', 'डार्क')}</button>
      </div>
    </section>
    <section className="settings-section" aria-labelledby="settings-install"><h2 id="settings-install">{t('Add CareCompass to your phone', 'CareCompass फ़ोन में जोड़ें')}</h2>
      <p>{t('Android: open the browser menu and choose Install app or Add to Home screen. iPhone: open in Safari, tap Share, then Add to Home Screen.', 'Android: ब्राउज़र मेन्यू खोलें और Install app या Add to Home screen चुनें। iPhone: Safari में खोलें, Share पर टैप करें, फिर Add to Home Screen चुनें।')}</p>
      <p>{t('An internet connection is required for care requests and voice.', 'देखभाल अनुरोध और वॉइस के लिए इंटरनेट कनेक्शन ज़रूरी है।')}</p>
    </section>
  </section>;
}
