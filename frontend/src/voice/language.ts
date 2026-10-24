import { createContext } from 'react';
import type { Language } from '../types';
export const VoiceLanguageContext = createContext<Language>('auto');

export const VoiceResponseContext = createContext<object | null>(null);

export const VoiceConversationContext = createContext<(() => void) | null>(null);
export const VoiceSessionActiveContext = createContext(false);

export const VoiceComposerHostContext = createContext<((node: HTMLDivElement | null) => void) | null>(null);
