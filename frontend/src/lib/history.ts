import type { Language, Location, Message, TriageResponse } from '../types.ts';
import { validateTriage } from './contracts.ts';
export interface CareConversation {
  id: string; title: string; input: string; language: Language;
  location: Location; messages: Message[]; result: TriageResponse; updatedAt: string; customTitle?: string;
}
export const HISTORY_KEY = 'carecompass.conversations.v1';
export function recentConversations(history: CareConversation[]): CareConversation[] {
  return [...history].sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt)).slice(0, 5);
}
export function saveConversation(history: CareConversation[], conversation: CareConversation): CareConversation[] {
  const customTitle = history.find(item => item.id === conversation.id)?.customTitle;
  return [{ ...conversation, ...(customTitle ? { customTitle, title: customTitle } : {}) }, ...history.filter(item => item.id !== conversation.id)];
}
export function readHistory(storage: Pick<Storage, 'getItem'>): CareConversation[] {
  try {
    const value: unknown = JSON.parse(storage.getItem(HISTORY_KEY) || '[]');
    if (!Array.isArray(value)) return [];
    return value.filter((entry): entry is CareConversation => {
      try {
        if (!entry || typeof entry.id !== 'string' || typeof entry.title !== 'string' || typeof entry.input !== 'string' || !['en', 'hi', 'hinglish', 'auto'].includes(entry.language) || !Number.isFinite(Date.parse(entry.updatedAt)) || !entry.location || typeof entry.location.label !== 'string' || !Number.isFinite(entry.location.lat) || !Number.isFinite(entry.location.lng) || !Array.isArray(entry.messages) || !entry.messages.every((m: Message) => m && ['user', 'assistant'].includes(m.role) && typeof m.content === 'string')) return false;
        validateTriage(entry.result);
        return true;
      } catch { return false; }
    });
  } catch { return []; }
}

export function requestHistory(messages: Message[]): Message[] {
  // Keep complete user/assistant pairs inside the backend's 40-turn limit.
  return messages.slice(-40);
}
