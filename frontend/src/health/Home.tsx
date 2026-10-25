import { ArrowRight, FileText, Upload } from 'lucide-react';
import { useHealth } from './Store';
import { DemoNote, HealthHeading, words } from './ui';
import { categoryHi } from './data';
import { formatDate } from '../lib/flow';
export function HealthHome({ hi, navigate, onUpload }: { hi: boolean; navigate: (page: 'records' | 'summary') => void; onUpload: () => void }) {
  const { state } = useHealth(); const t = words(hi);
  const data = state;
  return <><HealthHeading title={t('Your health at a glance.', 'आपके स्वास्थ्य की एक झलक।')} description={t('Your records and health history, in one place.', 'आपके रिकॉर्ड और स्वास्थ्य इतिहास, एक जगह।')} />
    <div className="briefcase-home-intro"><section className="health-upload-panel"><div><h2>{t('Every record. One place.', 'हर रिकॉर्ड, एक जगह।')}</h2><p>{t('Add a report or prescription. Build a health story you can come back to.', 'रिपोर्ट या प्रिस्क्रिप्शन जोड़ें। अपना स्वास्थ्य इतिहास एक जगह रखें।')}</p></div><button className="button primary" onClick={onUpload}><Upload size={18} />{t('Add health records', 'स्वास्थ्य रिकॉर्ड जोड़ें')}</button><p className="small muted">{t('PDF, JPG or PNG · local demo upload', 'PDF, JPG या PNG · स्थानीय डेमो अपलोड')}</p></section>
</div>
    <div className="home-recent-records"><section className="health-block"><div className="health-block-heading"><h2>{t('Recent records', 'हाल के रिकॉर्ड')}</h2><button className="text-button" onClick={() => navigate('records')}>{t('View records', 'रिकॉर्ड देखें')}<ArrowRight size={16}/></button></div><div className="compact-records">{data.records.slice().sort((a,b)=>b.date.localeCompare(a.date)).slice(0,3).map(r => <button key={r.id} onClick={() => navigate('records')} className="compact-record"><FileText size={20} /><span><strong>{r.title}</strong><small>{hi ? categoryHi[r.category] : r.category} · {formatDate(r.date, hi)}</small></span><ArrowRight size={16} /></button>)}</div><div className="record-count"><strong>{data.records.length}</strong><span>{t('records in your briefcase', 'रिकॉर्ड आपके ब्रीफ़केस में')}</span></div></section></div>
    <section className="health-summary-banner"><div><h2>{t('The bigger picture of your health.', 'आपके स्वास्थ्य की पूरी तस्वीर।')}</h2><p>{t('A timeline of records, readings and medications in this workspace. Sample data, not a doctor-reviewed assessment.', 'इस संग्रह के रिकॉर्ड, रीडिंग और दवाओं की समयरेखा। नमूना डेटा, डॉक्टर का मूल्यांकन नहीं।')}</p></div><button className="button secondary" onClick={() => navigate('summary')}>{t('View health summary', 'स्वास्थ्य सारांश देखें')}<ArrowRight size={17} /></button></section><DemoNote hi={hi} />
  </>;
}
