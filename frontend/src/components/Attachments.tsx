import { useEffect, useId, useRef, useState } from 'react';
import { Check, FileText, ImagePlus, Plus, UserPlus, UserRound, Users, X } from 'lucide-react';
import { useHealth } from '../health/Store';
import { localDate } from '../lib/flow';
import type { HealthRecord } from '../health/types';
import { isSelf } from './CareFor';

export function Attachments({ hindi, disabled, onProfile }: { hindi: boolean; disabled: boolean; onProfile?: () => void }) {
  const { state, setState, registerUrl } = useHealth();
  const [open, setOpen] = useState(false), [error, setError] = useState('');
  const [added, setAdded] = useState<HealthRecord[]>([]);
  const wrapper = useRef<HTMLDivElement>(null), trigger = useRef<HTMLButtonElement>(null);
  const reports = useRef<HTMLInputElement>(null), photos = useRef<HTMLInputElement>(null);
  const id = useId();
  const t = (en: string, hi: string) => hindi ? hi : en;
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => { if (!wrapper.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { setOpen(false); trigger.current?.focus(); } };
    document.addEventListener('pointerdown', outside); document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape); };
  }, [open]);
  function pick(files: FileList | null) {
    const list = Array.from(files ?? []); if (!list.length) return;
    if (added.length + list.length > 10 || list.some(file => !['application/pdf', 'image/jpeg', 'image/png'].includes(file.type) || !file.size || file.size > 10 * 1024 * 1024)) {
      setError(t('Choose up to 10 PDF, JPG or PNG files, up to 10 MB each.', 'अधिकतम 10 PDF, JPG या PNG फ़ाइलें चुनें, हर फ़ाइल 10 MB तक।')); return;
    }
    const records: HealthRecord[] = list.map(file => {
      const url = URL.createObjectURL(file); registerUrl(url);
      return { id: crypto.randomUUID(), memberId: state.activeId, title: file.name, category: 'Lab report', date: localDate(), source: 'Care request attachment', status: 'Awaiting extraction', description: 'Saved locally in this tab. Document analysis is not connected.', url, fileType: file.type, tags: ['Attachment'] };
    });
    setState(previous => ({ ...previous, records: [...records, ...previous.records] }));
    setAdded(previous => [...previous, ...records]); setError(''); setOpen(false); trigger.current?.focus();
  }
  const members = [...state.members].sort((a, b) => Number(isSelf(b.relation)) - Number(isSelf(a.relation)));
  function chooseMember(id: string) { setState(previous => ({ ...previous, activeId: id, careForOther: false })); setOpen(false); trigger.current?.focus(); }
  function chooseOther() { setState(previous => ({ ...previous, careForOther: true })); setOpen(false); trigger.current?.focus(); }
  function remove(record: HealthRecord) {
    setAdded(previous => previous.filter(item => item.id !== record.id));
    setState(previous => ({ ...previous, records: previous.records.filter(item => item.id !== record.id) }));
    if (record.url) URL.revokeObjectURL(record.url);
  }
  return <div className="care-attachments" ref={wrapper}>
    <button ref={trigger} type="button" className="icon-button care-attach-button" disabled={disabled} aria-label={t('Add files, photos or choose who this is for', 'फ़ाइलें जोड़ें या चुनें कि यह किसके लिए है')} title={t('Files, photos and who this is for', 'फ़ाइलें और यह किसके लिए है')} aria-expanded={open} aria-controls={id} onClick={() => setOpen(value => !value)}><Plus size={22}/></button>
    {open ? <div id={id} className="care-attachment-menu" role="group" aria-label={t('Care options', 'देखभाल विकल्प')}>
      <p className="care-menu-heading" id={`${id}-for`}>{t('Who is this for?', 'यह किसके लिए है?')}</p>
      <div className="care-for-list" role="group" aria-labelledby={`${id}-for`}>
        {members.map(member => { const on = !state.careForOther && member.id === state.activeId; return <button key={member.id} type="button" className="care-for-option" aria-pressed={on} disabled={disabled} onClick={() => chooseMember(member.id)}><UserRound size={17}/><span>{isSelf(member.relation) ? t('Myself', 'मेरे लिए') : member.name}<small>{isSelf(member.relation) ? member.name : member.relation}</small></span>{on ? <Check size={16} aria-hidden="true"/> : null}</button>; })}
        <button type="button" className="care-for-option" aria-pressed={!!state.careForOther} disabled={disabled} onClick={chooseOther}><Users size={17}/><span>{t('Someone else', 'किसी और के लिए')}<small>{t('Not in my profile · no saved details used', 'प्रोफ़ाइल में नहीं · सहेजी जानकारी इस्तेमाल नहीं होगी')}</small></span>{state.careForOther ? <Check size={16} aria-hidden="true"/> : null}</button>
        {onProfile ? <button type="button" className="care-for-option care-for-add" disabled={disabled} onClick={() => { setOpen(false); onProfile(); }}><UserPlus size={17}/><span>{t('Add a family member', 'परिवार का सदस्य जोड़ें')}</span></button> : null}
      </div>
      {state.shareProfile === false ? <p>{t('Profile sharing is off in Settings, so saved details are not sent.', 'सेटिंग्स में प्रोफ़ाइल साझा करना बंद है, इसलिए सहेजी जानकारी नहीं भेजी जाती।')}</p> : null}
      <hr className="care-menu-divider"/>
      <button type="button" disabled={disabled} onClick={() => reports.current?.click()}><FileText size={17}/>{t('Lab reports and files', 'लैब रिपोर्ट और फ़ाइलें')}</button>
      <button type="button" disabled={disabled} onClick={() => photos.current?.click()}><ImagePlus size={17}/>{t('Photos and images', 'फ़ोटो और तस्वीरें')}</button>
      <p>{t('PDF, JPG, PNG · up to 10 MB each', 'PDF, JPG, PNG · हर फ़ाइल 10 MB तक')}</p>
    </div> : null}
    <input ref={reports} type="file" hidden multiple accept="application/pdf,image/jpeg,image/png" aria-label={t('Choose lab reports and files', 'लैब रिपोर्ट और फ़ाइलें चुनें')} onChange={event => { pick(event.target.files); event.target.value = ''; }}/>
    <input ref={photos} type="file" hidden multiple accept="image/jpeg,image/png" aria-label={t('Choose photos and images', 'फ़ोटो और तस्वीरें चुनें')} onChange={event => { pick(event.target.files); event.target.value = ''; }}/>
    {added.length ? <div className="care-attachment-list" aria-label={t('Added files', 'जोड़ी गई फ़ाइलें')}>{added.map(record => <span key={record.id}><FileText size={15}/><span title={record.title}>{record.title}</span><button type="button" className="icon-button" disabled={disabled} aria-label={`${t('Remove', 'हटाएँ')} ${record.title}`} onClick={() => remove(record)}><X size={14}/></button></span>)}<p role="status">{t('Saved to Briefcase. File contents stay in this tab; document analysis is not connected.', 'ब्रीफ़केस में सुरक्षित। फ़ाइल की सामग्री इसी टैब में रहती है; दस्तावेज़ विश्लेषण जुड़ा नहीं है।')}</p></div> : null}
    {error ? <p className="care-attachment-error" role="alert">{error}</p> : null}
  </div>;
}
