import { ArrowUp, MapPin } from 'lucide-react';
import { useContext, useId } from 'react';
import { scenarios } from '../data';
import type { IntakeProps } from './Intake';
import { VoiceInput } from './Voice';
import { Attachments } from './Attachments';
import { VoiceComposerSlot } from './VoiceComposerSlot';
import { VoiceSessionActiveContext } from '../voice/language';

export function ChatIntake({copy,hindi,language,input,setInput,location,busy,error,onSubmit,onLocation}:IntakeProps) {
  const voiceActive = useContext(VoiceSessionActiveContext);
  const t = (en:string,hi:string) => hindi ? hi : en;
  const inputId = useId(); const hintId = useId(); const errorId = useId();
  return <section className="chat-intake" aria-label={copy.findCare}>
    <div className="chat-intake-heading"><h1 tabIndex={-1}>{t('What care do you need?', 'आपको किस देखभाल की ज़रूरत है?')}</h1><p>{t('A few words. A clearer next step.', 'कुछ शब्दों से, अगला कदम साफ़।')}</p></div>
    <form className="care-chat-form" onSubmit={e=>{e.preventDefault();onSubmit();}}>
      <label htmlFor={inputId} className="care-input-label">{copy.inputLabel}</label>
      <div className="care-chat-composer">{voiceActive ? <VoiceComposerSlot/> : null}<div hidden={voiceActive}><textarea id={inputId} rows={1} maxLength={2000} value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();if(input.trim()&&!busy)onSubmit();}}} placeholder={t('Describe how you’re feeling…','अपनी परेशानी बताएँ…')} disabled={busy} aria-invalid={!!error} aria-describedby={`${hintId}${error?` ${errorId}`:''}`}/>
        <div className="care-chat-actions"><Attachments hindi={hindi} disabled={busy}/><div className="care-send-actions"><VoiceInput copy={copy} hindi={hindi} disabled={busy} onTranscript={text=>setInput(`${input}${input?' ':''}${text}`.slice(0,2000))}/><button type="submit" className={`care-send${input.trim()?' has-message':''}`} disabled={busy||!input.trim()} aria-label={busy?copy.checking:copy.continue} title={copy.continue}>{input.trim()?<span>{busy?copy.checking:copy.continue}</span>:null}{busy?<span className="spinner" aria-hidden="true"/>:<ArrowUp size={22}/>}</button></div></div>
      </div></div>
      {error?<p className="error-message" role="alert" id={errorId}>{error}</p>:null}
      <p className="care-input-hint" id={hintId}>{busy?copy.checking:t('Type or speak in English, हिंदी or Hinglish.', 'English, हिंदी या Hinglish में लिखें या बोलें।')}</p>
      <div className="care-sample-prompts" aria-label={copy.examples}>{scenarios.map(s=><button key={s.id} type="button" disabled={busy} onClick={()=>setInput(hindi?s.textHi:language==='hinglish'?s.hinglish:s.text)}>{hindi?s.hi:s.en}</button>)}</div>
    </form>
    <div className="care-intake-bottom"><button className="care-location-shortcut" onClick={onLocation} disabled={busy}><MapPin size={14}/>{location.lat===0?copy.outside:location.label}<span>{copy.locationDemo}</span></button><p>{t('Synthetic examples only. No diagnosis or real appointments.', 'सिर्फ़ काल्पनिक उदाहरण। कोई निदान या वास्तविक बुकिंग नहीं।')}</p><details><summary>{t('About voice input', 'आवाज़ से इनपुट के बारे में')}</summary><p>{copy.voiceNotice}</p></details></div>
  </section>;
}
