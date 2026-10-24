import { useState } from 'react';
import { ArrowLeft, ArrowRight, MessageSquare } from 'lucide-react';
import type { CareConversation } from '../lib/history';
export function ChatHistory({ history, hindi, onOpen, onNew }: { history: CareConversation[]; hindi: boolean; onOpen: (conversation: CareConversation) => void; onNew: () => void }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = history.find(item => item.id === selectedId);
  const t = (en: string, hi: string) => hindi ? hi : en;
  return <section className="care-history" aria-label={t('Chat history', 'बातचीत का इतिहास')}>
    <div className="page-heading"><h1>{t('Your conversations.', 'आपकी बातचीत।')}</h1><p>{t('Revisit a care request or pick up where you left off.', 'पिछली बातचीत देखें या वहीं से जारी रखें।')}</p></div>
    <p className="small muted">{t('Saved in this tab only. Refreshing clears chat history.', 'केवल इस टैब में सुरक्षित। रीफ़्रेश करने पर इतिहास मिट जाएगा।')}</p>
    {selected ? <div className="care-history-detail"><button className="text-button" onClick={() => setSelectedId(null)}><ArrowLeft size={17}/>{t('All conversations', 'सभी बातचीत')}</button><h2>{selected.title}</h2><ol className="chat-thread">{selected.messages.map((message, index) => <li key={index} className={`chat-bubble ${message.role}`}><span className="chat-bubble-from">{message.role === 'user' ? t('You', 'आप') : 'CareCompass'}</span><p>{message.role === 'user' && index === 0 ? selected.input : message.content}</p></li>)}</ol><button className="button primary" onClick={() => onOpen(selected)}>{t('Open conversation', 'बातचीत खोलें')}<ArrowRight size={17}/></button></div>
      : history.length ? <div className="care-history-list">{history.map(item => <button key={item.id} onClick={() => setSelectedId(item.id)}><MessageSquare size={19}/><span><strong>{item.title}</strong><small>{new Intl.DateTimeFormat(hindi ? 'hi-IN' : 'en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(item.updatedAt))}</small></span><ArrowRight size={17}/></button>)}</div>
      : <div className="care-history-empty"><MessageSquare size={28}/><h2>{t('A fresh start.', 'एक नई शुरुआत।')}</h2><p>{t('Your care conversations will appear here after a reply.', 'जवाब आने के बाद आपकी बातचीत यहाँ दिखाई देगी।')}</p><button className="button primary" onClick={onNew}>{t('Start a conversation', 'बातचीत शुरू करें')}<ArrowRight size={17}/></button></div>}
  </section>;
}
