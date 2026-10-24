import { useEffect, useRef, useState } from 'react';
import { Activity, ArrowRight, Bell, BriefcaseMedical, CalendarHeart, ChevronDown, FileHeart, FlaskConical, Globe2, HeartHandshake, House, IdCard, Menu, MessageCircle, MoreHorizontal, Pill, Settings2, Users, X } from 'lucide-react';
import App from '../App';
import { Modal } from '../components/Modal';
import { localDate } from '../lib/flow';
import { HealthProvider, useHealth } from './Store';
import type { HealthPage } from './types';
import type { Language } from '../types';
import { HealthHome } from './Home';
import { Records } from './Records';
import { HealthSummary, Labs, Vitals } from './Readings';
import { Medications } from './Medications';
import { Ask } from './Ask';
import { ABHA, Family } from './Family';
import { Services } from './Services';
import { Messages } from './Messages';
import { Settings } from './Settings';
import { MemberAvatar, words } from './ui';

const destinations = [
  {id:'home',en:'Home',hi:'होम',Icon:House}, {id:'records',en:'Briefcase',hi:'ब्रीफ़केस',Icon:BriefcaseMedical},
  {id:'summary',en:'Health summary',hi:'स्वास्थ्य सारांश',Icon:FileHeart}, {id:'vitals',en:'Vitals',hi:'वाइटल्स',Icon:Activity},
  {id:'labs',en:'Labs',hi:'लैब',Icon:FlaskConical}, {id:'medications',en:'Medications',hi:'दवाएँ',Icon:Pill},
  {id:'ask',en:'Ask CareCompass',hi:'CareCompass से पूछें',Icon:MessageCircle}, {id:'care',en:'Find care',hi:'देखभाल खोजें',Icon:HeartHandshake},
  {id:'appointments',en:'Care appointments',hi:'देखभाल अपॉइंटमेंट',Icon:CalendarHeart},
  {id:'family',en:'Family profiles',hi:'परिवार की प्रोफ़ाइल',Icon:Users}, {id:'abha',en:'ABHA preview',hi:'ABHA प्रीव्यू',Icon:IdCard},
  {id:'services',en:'Health services',hi:'स्वास्थ्य सेवाएँ',Icon:CalendarHeart}, {id:'messages',en:'Messages & updates',hi:'संदेश और अपडेट',Icon:Bell},
  {id:'settings',en:'Workspace settings',hi:'कार्यस्थल सेटिंग',Icon:Settings2},
] as const;
function Workspace() {
  const {state,setState,reset,version}=useHealth();const [page,setPage]=useState<HealthPage>('home');const [language,setLanguage]=useState<Language>('en');const hi=language==='hi';const [menu,setMenu]=useState(false);const [profilePicker,setProfilePicker]=useState(false);const [upload,setUpload]=useState(false);const t=words(hi);const content=useRef<HTMLElement>(null);
  const active=state.members.find(m=>m.id===state.activeId)!;const unread=state.notices.filter(n=>!n.read).length;
  function navigate(next:HealthPage){setPage(next);setMenu(false);setUpload(false);}
  function addRecord(){setPage('records');setUpload(true);}
  useEffect(()=>{document.documentElement.lang=hi?'hi':'en';},[hi]);
  useEffect(()=>{window.scrollTo({top:0,behavior:'instant'});content.current?.querySelector<HTMLElement>('h1')?.focus({preventScroll:true});},[page,state.activeId]);
  useEffect(()=>{
    function checkDue(){const now=new Date();const time=`${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;const today=localDate();setState(s=>{const notices=s.medications.filter(m=>m.active&&m.startDate<=today&&m.endDate>=today&&m.time<=time&&!s.doses.some(d=>d.medicationId===m.id&&d.date===today)&&!s.notices.some(n=>n.id===`REMINDER_${m.id}_${today}`)).map(m=>({id:`REMINDER_${m.id}_${today}`,title:`${s.members.find(p=>p.id===m.memberId)?.name}: ${m.name}`,body:'In-app demo reminder. Follow existing prescriber instructions; this app gives no dose advice.',read:false,page:'medications' as const}));return notices.length?{...s,notices:[...notices,...s.notices]}:s;});}
    checkDue();const interval=window.setInterval(checkDue,30000);return()=>window.clearInterval(interval);
  },[setState]);
  return <div className="health-portal"><a className="skip-link" href="#workspace-main">{t('Skip to main content','मुख्य भाग पर जाएँ')}</a><header className="portal-header"><div><button className="brand" onClick={()=>navigate('home')} aria-label="CareCompass home"><img src="/compass.svg" alt="" width="32" height="32"/><span>CareCompass</span></button><span className="portal-context">{t('Your family health workspace','परिवार का स्वास्थ्य कार्यस्थल')}</span><div className="portal-header-actions"><label className="language-control"><Globe2 size={17}/><select aria-label={t('Language','भाषा')} value={language} onChange={e=>setLanguage(e.target.value as Language)}><option value="en">English</option><option value="hi">हिंदी</option><option value="hinglish">Hinglish</option><option value="auto">Auto</option></select></label><button className="icon-button notice-button" aria-label={`${t('Notifications','सूचनाएँ')} ${unread}`} onClick={()=>navigate('messages')}><Bell size={20}/>{unread?<span>{unread}</span>:null}</button><button className="portal-profile" onClick={()=>setProfilePicker(true)}><MemberAvatar member={active} small/><span>{active.name.split(' ')[0]}</span><ChevronDown size={14}/></button><button className="icon-button portal-menu-toggle" aria-label={t('Open navigation','नेविगेशन खोलें')} aria-expanded={menu} onClick={()=>setMenu(true)}><Menu size={22}/></button></div></div></header>
    <div className="portal-layout"><aside className="portal-sidebar"><span className="sidebar-caption">{t('Your health','आपका स्वास्थ्य')}</span><nav aria-label={t('Workspace','कार्यस्थल')}>{destinations.map(({id,en,hi:hin,Icon},i)=><button key={id} className={`${page===id?'active':''} ${i===8?'nav-group-start':''}`} aria-current={page===id?'page':undefined} onClick={()=>navigate(id)}><Icon size={18} strokeWidth={1.7}/><span>{t(en,hin)}</span></button>)}</nav><div className="sidebar-demo"><span className="demo-label"><span/>{t('Synthetic demo','कृत्रिम डेमो')}</span><p>{t('A personal health workspace, built with made-up data.','काल्पनिक डेटा से बना स्वास्थ्य कार्यस्थल।')}</p></div></aside>
    <main className="workspace-content" id="workspace-main" ref={content}><div className="workspace-breadcrumb"><span>{t('Health workspace','स्वास्थ्य कार्यस्थल')}</span><span>/</span><span>{active.name}</span><span className="workspace-demo">{t('Demo data','डेमो डेटा')}</span></div>
      {page==='home'?<HealthHome hi={hi} navigate={navigate} onUpload={addRecord}/>:null}
      {page==='records'?<Records key={state.activeId} hi={hi} openUpload={upload} onUploadClosed={()=>setUpload(false)} onSummary={()=>navigate('summary')}/>:null}
      {page==='summary'?<HealthSummary key={state.activeId} hi={hi} onRecords={()=>navigate('records')} onAsk={()=>navigate('ask')}/>:null}
      {page==='vitals'?<Vitals key={state.activeId} hi={hi}/>:null}
      {page==='labs'?<Labs hi={hi} onRecords={addRecord} onVitals={()=>navigate('vitals')}/>:null}
      {page==='medications'?<Medications key={state.activeId} hi={hi}/>:null}
      {page==='ask'?<Ask key={state.activeId} hi={hi} onCare={()=>navigate('care')}/>:null}
      {page==='family'?<Family hi={hi} onRecords={()=>navigate('records')}/>:null}
      {page==='abha'?<ABHA key={state.activeId} hi={hi}/>:null}
      {page==='services'?<Services key={state.activeId} hi={hi} onCare={()=>navigate('care')}/>:null}
      {page==='messages'?<Messages key={state.activeId} hi={hi} navigate={navigate}/>:null}
      {page==='settings'?<Settings hi={hi} onFamily={()=>navigate('family')} onReset={()=>{reset();navigate('home');}}/>:null}
      {state.members.map(member=><div className="embedded-flow" key={`${member.id}-${version}`} hidden={(page!=='care'&&page!=='appointments')||member.id!==state.activeId}><App embedded externalLanguage={language} patientName={member.name} externalBookings={page==='appointments'} onStartCare={()=>navigate('care')} onViewBookings={()=>navigate('appointments')}/></div>)}
      <footer className="workspace-footer"><span>CareCompass · Hack IIITD</span><span>{t('Care navigation, with your health story close by.','आपके स्वास्थ्य इतिहास के साथ देखभाल का मार्गदर्शन।')}</span></footer>
    </main></div>
    <nav className="portal-bottom-nav" aria-label={t('Quick navigation','त्वरित नेविगेशन')}>{[['home','Home','होम',House],['records','Briefcase','ब्रीफ़केस',BriefcaseMedical],['ask','Ask','पूछें',MessageCircle],['care','Find care','देखभाल',HeartHandshake]].map(([id,en,hin,Icon])=>{const I=Icon as typeof House;return <button key={id as string} className={page===id?'active':''} aria-current={page===id?'page':undefined} onClick={()=>navigate(id as HealthPage)}><I size={20}/><span>{t(en as string,hin as string)}</span></button>;})}<button onClick={()=>setMenu(true)} aria-label={t('More pages','और पेज')}><MoreHorizontal size={21}/><span>{t('More','और')}</span></button></nav>
    {menu?<Modal title={t('Your health workspace','आपका स्वास्थ्य कार्यस्थल')} closeLabel={t('Close','बंद करें')} onClose={()=>setMenu(false)}><nav className="portal-drawer">{destinations.map(({id,en,hi:hin,Icon})=><button key={id} aria-current={page===id?'page':undefined} onClick={()=>navigate(id)}><Icon size={19}/>{t(en,hin)}{page===id?<span>•</span>:<ArrowRight size={15}/>}</button>)}</nav></Modal>:null}
    {profilePicker?<Modal title={t('Whose health are we looking at?','किसका स्वास्थ्य देख रहे हैं?')} closeLabel={t('Close','बंद करें')} onClose={()=>setProfilePicker(false)}><div className="profile-picker">{state.members.map(m=><button key={m.id} className={m.id===state.activeId?'active':''} onClick={()=>{setState(s=>({...s,activeId:m.id}));setProfilePicker(false);}}><MemberAvatar member={m}/><span><strong>{m.name}</strong><small>{m.relation} · {m.age} {t('years','वर्ष')}</small></span><ArrowRight size={17}/></button>)}</div><button className="text-button" onClick={()=>{setProfilePicker(false);navigate('family');}}><Users size={17}/>{t('Manage family profiles','परिवार की प्रोफ़ाइल सँभालें')}</button></Modal>:null}
  </div>;
}
export default function Portal(){return <HealthProvider><Workspace/></HealthProvider>;}
