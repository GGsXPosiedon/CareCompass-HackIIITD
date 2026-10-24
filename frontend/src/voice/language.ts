import { createContext } from 'react';
import type { Language } from '../types';
export const VoiceLanguageContext = createContext<Language>('en');
