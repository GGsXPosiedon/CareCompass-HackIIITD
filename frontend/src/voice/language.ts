import { createContext } from 'react';
import type { Language } from '../types';
export const VoiceLanguageContext = createContext<Language>('en');

export const VoiceResponseContext = createContext<object | null>(null);
