import { useState } from 'react';
import { Check, Pencil, Trash2, X } from 'lucide-react';
import type { CareConversation } from '../lib/history';
import { recentConversations } from '../lib/history';

export function ConversationSidebar({ history, activeId, hindi, onOpen, onRename, onDelete }: {
  history: CareConversation[]; activeId: string | null; hindi: boolean;
  onOpen: (entry: CareConversation) => void; onRename: (id: string, title: string) => void; onDelete: (id: string) => void;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const t = (en: string, hi: string) => hindi ? hi : en;
  return <section className="sidebar-conversations" aria-label={t('Recent conversations', 'हाल की बातचीत')}>
    <h2>{t('Recents', 'हाल की बातचीत')}</h2>
    {history.length ? <ul>{recentConversations(history).map(entry => <li key={entry.id} className={activeId === entry.id ? 'is-active' : ''}>
      {editing === entry.id ? <form onSubmit={event => { event.preventDefault(); if (title.trim()) { onRename(entry.id, title.trim().slice(0, 100)); setEditing(null); } }}>
        <input autoFocus aria-label={t('Conversation title', 'बातचीत का शीर्षक')} maxLength={100} value={title} onChange={event => setTitle(event.target.value)} onKeyDown={event => { if (event.key === 'Escape') setEditing(null); }}/>
        <button type="submit" disabled={!title.trim()} aria-label={t('Save title', 'शीर्षक सुरक्षित करें')}><Check size={14}/></button><button type="button" onClick={() => setEditing(null)} aria-label={t('Cancel rename', 'नाम बदलना रद्द करें')}><X size={14}/></button>
      </form> : <>
        <button className="sidebar-conversation-open" onClick={() => onOpen(entry)} title={entry.title} aria-current={activeId === entry.id ? 'true' : undefined}>{entry.title}</button>
        <div className="sidebar-conversation-actions"><button onClick={() => { setEditing(entry.id); setTitle(entry.title); }} aria-label={`${t('Rename', 'नाम बदलें')}: ${entry.title}`}><Pencil size={13}/></button><button onClick={() => onDelete(entry.id)} aria-label={`${t('Delete', 'मिटाएँ')}: ${entry.title}`}><Trash2 size={13}/></button></div>
      </>}
    </li>)}</ul> : <p>{t('Your conversations appear here.', 'आपकी बातचीत यहाँ दिखाई देगी।')}</p>}
    <p className="sidebar-history-note">{t('Saved on this device. Delete chats to remove them.', 'इस डिवाइस पर सुरक्षित। हटाने के लिए चैट मिटाएँ।')}</p>
  </section>;
}
