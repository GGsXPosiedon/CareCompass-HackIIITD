import type { Language, Location, Message, TriageResponse } from '../types.ts';
export interface CareConversation {
  id: string; title: string; input: string; person: string; language: Language;
  location: Location; messages: Message[]; result: TriageResponse; updatedAt: string;
}
export function saveConversation(history: CareConversation[], conversation: CareConversation): CareConversation[] {
  return [conversation, ...history.filter(item => item.id !== conversation.id)];
}
