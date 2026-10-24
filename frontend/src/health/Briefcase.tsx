import { useState } from 'react';
import { HealthHome } from './Home';
import { Records } from './Records';
import { HealthSummary, Labs } from './Readings';
import { words } from './ui';

type BriefcasePage = 'home' | 'records' | 'summary' | 'labs';
const tabs = [
  ['home', 'Home', 'होम'],
  ['records', 'Records', 'रिकॉर्ड'],
  ['summary', 'Health summary', 'स्वास्थ्य सारांश'],
  ['labs', 'Labs', 'लैब'],
] as const;

export default function Briefcase({ hi }: { hi: boolean }) {
  const [page, setPage] = useState<BriefcasePage>('records');
  const [upload, setUpload] = useState(false);
  const t = words(hi);
  function navigate(next: BriefcasePage) { setPage(next); setUpload(false); window.scrollTo({top:0,behavior:'instant'}); }
  function addRecord() { setPage('records'); setUpload(true); }
  return <div className="health-portal briefcase-content">
    <nav className="briefcase-tabs" aria-label={t('Briefcase sections', 'ब्रीफ़केस के भाग')}>
      {tabs.map(([id, en, hindi]) => <button key={id} aria-current={page === id ? 'page' : undefined} className={page === id ? 'active' : ''} onClick={() => navigate(id)}>{t(en, hindi)}</button>)}
    </nav>
    {page === 'home' ? <HealthHome hi={hi} navigate={navigate} onUpload={addRecord}/> : null}
    {page === 'records' ? <Records hi={hi} openUpload={upload} onUploadClosed={() => setUpload(false)} onSummary={() => navigate('summary')}/> : null}
    {page === 'summary' ? <HealthSummary hi={hi} onRecords={() => navigate('records')}/> : null}
    {page === 'labs' ? <Labs hi={hi} onRecords={() => navigate('records')} onUpload={addRecord}/> : null}
  </div>;
}
