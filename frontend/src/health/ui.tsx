import { ArrowRight, FileText, ShieldCheck } from 'lucide-react';
import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import type { HealthPage, Member } from './types';
export function words(hi: boolean) { return (english: string, hindi: string) => hi ? hindi : english; }
export function MemberAvatar({ member, small = false }: { member: Member; small?: boolean }) { return <span className={`avatar ${member.tint} ${small ? 'small-avatar' : ''}`} aria-hidden="true">{member.initials}</span>; }
export function HealthHeading({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { if (heading.current?.getClientRects().length) heading.current.focus({preventScroll:true}); }, [title]);
  return <div className="health-heading"><div><h1 ref={heading} tabIndex={-1}>{title}</h1><p>{description}</p></div>{action}</div>;
}
export function DemoNote({ hi, children }: { hi: boolean; children?: ReactNode }) { const t = words(hi); return <p className="health-demo-note"><ShieldCheck size={16} /><span>{children ?? t('Synthetic demo. Changes stay in this tab and clear on refresh. Use made-up information only.', 'कृत्रिम डेमो। बदलाव केवल इस टैब में रहते हैं और रीफ़्रेश पर मिट जाते हैं। सिर्फ़ काल्पनिक जानकारी दें।')}</span></p>; }
export function Empty({ title, body, action }: { title: string; body: string; action?: ReactNode }) { return <div className="health-empty"><FileText size={28} /><h2>{title}</h2><p>{body}</p>{action}</div>; }
export function PageLink({ page, onNavigate, children }: { page: HealthPage; onNavigate: (page: HealthPage) => void; children: ReactNode }) { return <button className="text-button" onClick={() => onNavigate(page)}>{children}<ArrowRight size={16} /></button>; }
