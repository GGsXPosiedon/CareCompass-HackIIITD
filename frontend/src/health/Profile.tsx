import { useState } from 'react';
import { Plus, ShieldCheck, Trash2 } from 'lucide-react';
import { useHealth } from './Store';
import { HealthHeading, MemberAvatar, words } from './ui';
import { formatDate } from '../lib/flow';
import type { Member } from './types';

const TINTS = ['sage', 'blue', 'rose', 'sand'];
const list = (value: string) => value.split(/[\n,]/).map(v => v.trim()).filter(Boolean).slice(0, 20);
const initialsOf = (name: string) => name.trim().split(/\s+/).slice(0, 2).map(w => w[0]?.toUpperCase() ?? '').join('') || '?';

function MemberForm({ hi, initial, onSave, onCancel }: { hi: boolean; initial?: Member; onSave: (m: Omit<Member, 'id' | 'initials' | 'tint'>) => void; onCancel?: () => void }) {
  const t = words(hi);
  const [name, setName] = useState(initial?.name ?? '');
  const [relation, setRelation] = useState(initial?.relation ?? '');
  const [age, setAge] = useState(initial ? String(initial.age) : '');
  const [sex, setSex] = useState(initial?.sex ?? '');
  const [blood, setBlood] = useState(initial?.bloodGroup ?? '');
  const [conditions, setConditions] = useState((initial?.conditions ?? []).join(', '));
  const [allergies, setAllergies] = useState((initial?.allergies ?? []).join(', '));
  const years = Number(age);
  const valid = name.trim().length > 0 && Number.isInteger(years) && years >= 0 && years <= 120;
  return <form className="profile-form" onSubmit={event => { event.preventDefault(); if (valid) onSave({ name: name.trim().slice(0, 60), relation: relation.trim().slice(0, 30), age: years, sex: sex || undefined, bloodGroup: blood.trim().slice(0, 4), conditions: list(conditions), allergies: list(allergies) }); }}>
    <label>{t('Full name', 'पूरा नाम')}<input value={name} maxLength={60} onChange={e => setName(e.target.value)} required /></label>
    <label>{t('Relation', 'रिश्ता')}<input value={relation} maxLength={30} placeholder={t('Myself, Father, Mother…', 'मैं, पिता, माता…')} onChange={e => setRelation(e.target.value)} /></label>
    <label>{t('Age', 'उम्र')}<input value={age} inputMode="numeric" onChange={e => setAge(e.target.value.replace(/\D/g, '').slice(0, 3))} required /></label>
    <label>{t('Sex', 'लिंग')}<select value={sex} onChange={e => setSex(e.target.value)}><option value="">{t('Not specified', 'नहीं बताया')}</option><option value="female">{t('Female', 'महिला')}</option><option value="male">{t('Male', 'पुरुष')}</option><option value="other">{t('Other', 'अन्य')}</option></select></label>
    <label>{t('Blood group', 'ब्लड ग्रुप')}<input value={blood} maxLength={4} placeholder="O+" onChange={e => setBlood(e.target.value)} /></label>
    <label className="wide">{t('Medical conditions (comma separated)', 'स्वास्थ्य स्थितियाँ (कॉमा से अलग करें)')}<textarea rows={2} value={conditions} onChange={e => setConditions(e.target.value)} /></label>
    <label className="wide">{t('Allergies (comma separated)', 'एलर्जी (कॉमा से अलग करें)')}<textarea rows={2} value={allergies} onChange={e => setAllergies(e.target.value)} /></label>
    <div className="profile-form-actions"><button type="submit" className="button primary" disabled={!valid}>{t('Save', 'सहेजें')}</button>{onCancel ? <button type="button" className="button secondary" onClick={onCancel}>{t('Cancel', 'रद्द करें')}</button> : null}</div>
  </form>;
}

export default function Profile({ hi }: { hi: boolean }) {
  const t = words(hi);
  const { state, setState } = useHealth();
  const member = state.members.find(m => m.id === state.activeId) ?? state.members[0];
  const [mode, setMode] = useState<'view' | 'edit' | 'add'>('view');
  const meds = state.medications.filter(m => m.memberId === member?.id && m.active);
  const records = [...state.records].filter(r => r.memberId === member?.id).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 5);
  const metrics = [...new Set(state.readings.filter(r => r.memberId === member?.id).map(r => r.metric))];
  const latest = metrics.map(metric => [...state.readings].filter(r => r.memberId === member?.id && r.metric === metric).sort((a, b) => b.date.localeCompare(a.date) || b.time.localeCompare(a.time))[0]);

  function select(id: string) { setState(s => ({ ...s, activeId: id })); setMode('view'); }
  function save(values: Omit<Member, 'id' | 'initials' | 'tint'>) {
    if (mode === 'add') {
      const id = `P_${Date.now().toString(36)}`;
      setState(s => ({ ...s, members: [...s.members, { ...values, id, initials: initialsOf(values.name), tint: TINTS[s.members.length % TINTS.length] }], activeId: id }));
    } else if (member) {
      setState(s => ({ ...s, members: s.members.map(m => m.id === member.id ? { ...m, ...values, initials: initialsOf(values.name) } : m) }));
    }
    setMode('view');
  }
  function remove() {
    if (!member || state.members.length < 2) return;
    setState(s => { const members = s.members.filter(m => m.id !== member.id); return { ...s, members, activeId: members[0].id }; });
  }

  return <div className="health-portal profile-content">
    <HealthHeading title={t('Profile & family', 'प्रोफ़ाइल और परिवार')} description={t('Details you save here are available to the care assistant, so you do not have to repeat them.', 'यहाँ सहेजी गई जानकारी केयर असिस्टेंट के पास रहती है, ताकि आपको दोहरानी न पड़े।')}
      action={<button className="button secondary" onClick={() => setMode('add')}><Plus size={16} />{t('Add family member', 'सदस्य जोड़ें')}</button>} />
    <section className="profile-share" aria-label={t('Assistant access', 'असिस्टेंट की पहुँच')}>
      <ShieldCheck size={18} />
      <div><strong>{t('Share this profile with the care assistant', 'यह प्रोफ़ाइल केयर असिस्टेंट के साथ साझा करें')}</strong>
        <p>{t('When on, saved conditions, allergies, medicines and recent records are sent with your request to the Gemini AI service to improve triage. Turn off to keep them private.', 'चालू होने पर, सहेजी गई स्थितियाँ, एलर्जी, दवाएँ और हाल के रिकॉर्ड आपके अनुरोध के साथ Gemini AI सेवा को भेजे जाते हैं। निजी रखने के लिए बंद करें।')}</p></div>
      <label className="switch"><input type="checkbox" checked={state.shareProfile !== false} onChange={e => setState(s => ({ ...s, shareProfile: e.target.checked }))} /><span className="sr-only">{t('Share profile', 'प्रोफ़ाइल साझा करें')}</span></label>
    </section>
    <div className="profile-layout">
      <ul className="profile-members" aria-label={t('Family members', 'परिवार के सदस्य')}>
        {state.members.map(m => <li key={m.id}><button className={m.id === member?.id ? 'active' : ''} aria-current={m.id === member?.id ? 'true' : undefined} onClick={() => select(m.id)}><MemberAvatar member={m} /><span><strong>{m.name}</strong><small>{m.relation || '—'} · {m.age}</small></span></button></li>)}
      </ul>
      <div className="profile-detail">
        {mode === 'add' ? <><h2>{t('New family member', 'नया सदस्य')}</h2><MemberForm hi={hi} onSave={save} onCancel={() => setMode('view')} /></> : null}
        {mode === 'edit' && member ? <><h2>{t('Edit profile', 'प्रोफ़ाइल संपादित करें')}</h2><MemberForm hi={hi} initial={member} onSave={save} onCancel={() => setMode('view')} /></> : null}
        {mode === 'view' && member ? <>
          <div className="profile-summary"><MemberAvatar member={member} /><div><h2>{member.name}</h2><p>{member.relation || '—'} · {member.age} {t('years', 'वर्ष')}{member.sex ? ` · ${member.sex}` : ''}{member.bloodGroup ? ` · ${member.bloodGroup}` : ''}</p></div>
            <div className="profile-actions"><button className="button secondary" onClick={() => setMode('edit')}>{t('Edit', 'संपादित करें')}</button>{state.members.length > 1 ? <button className="text-button" onClick={remove} aria-label={t(`Remove ${member.name}`, `${member.name} को हटाएँ`)}><Trash2 size={15} />{t('Remove', 'हटाएँ')}</button> : null}</div></div>
          <section><h3>{t('Medical history', 'चिकित्सा इतिहास')}</h3>
            <dl className="profile-facts">
              <div><dt>{t('Conditions', 'स्वास्थ्य स्थितियाँ')}</dt><dd>{member.conditions?.length ? member.conditions.join(', ') : t('None saved', 'कोई सहेजी नहीं')}</dd></div>
              <div><dt>{t('Allergies', 'एलर्जी')}</dt><dd>{member.allergies.length ? member.allergies.join(', ') : t('None saved', 'कोई सहेजी नहीं')}</dd></div>
              <div><dt>{t('Current medicines', 'वर्तमान दवाएँ')}</dt><dd>{meds.length ? meds.map(m => m.name).join(', ') : t('None saved', 'कोई सहेजी नहीं')}</dd></div>
            </dl></section>
          <section><h3>{t('Latest readings', 'ताज़ा रीडिंग')}</h3>
            {latest.length ? <ul className="profile-list">{latest.map(r => <li key={r.id}><span>{r.metric}</span><strong>{r.value}{r.secondary ? `/${r.secondary}` : ''}</strong><small>{formatDate(r.date, hi)}</small></li>)}</ul> : <p className="muted">{t('No readings yet.', 'अभी कोई रीडिंग नहीं।')}</p>}</section>
          <section><h3>{t('Recent records', 'हाल के रिकॉर्ड')}</h3>
            {records.length ? <ul className="profile-list">{records.map(r => <li key={r.id}><span>{r.title}</span><strong>{r.category}</strong><small>{formatDate(r.date, hi)}</small></li>)}</ul> : <p className="muted">{t('No records yet.', 'अभी कोई रिकॉर्ड नहीं।')}</p>}</section>
        </> : null}
      </div>
    </div>
  </div>;
}
