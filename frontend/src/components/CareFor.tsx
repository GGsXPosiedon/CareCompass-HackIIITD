import { UserRound } from 'lucide-react';
import { useHealth } from '../health/Store';
import type { HealthState } from '../health/types';

export interface CareForInfo { kind: 'self' | 'member' | 'other'; label: string }

export function isSelf(relation: string) { return /^(myself|self|me)$/i.test(relation.trim()); }

// Who the current request is for, derived from the saved profile state (no extra state to keep in sync).
export function careForOf(state: Pick<HealthState, 'members' | 'activeId' | 'careForOther'>, hindi: boolean): CareForInfo {
  if (state.careForOther) return { kind: 'other', label: hindi ? 'किसी और के लिए' : 'Someone else' };
  const member = state.members.find(m => m.id === state.activeId) ?? state.members[0];
  if (!member) return { kind: 'other', label: hindi ? 'किसी और के लिए' : 'Someone else' };
  return isSelf(member.relation) ? { kind: 'self', label: hindi ? 'मेरे लिए' : 'Myself' } : { kind: 'member', label: member.name.split(' ')[0] };
}

export function CareForChip({ hindi }: { hindi: boolean }) {
  const { state } = useHealth();
  const info = careForOf(state, hindi);
  return <span className="care-for-chip" data-kind={info.kind} title={hindi ? 'यह अनुरोध किसके लिए है' : 'Who this request is for'}><UserRound size={13} aria-hidden="true"/><span className="sr-only">{hindi ? 'किसके लिए: ' : 'For: '}</span>{info.label}</span>;
}
