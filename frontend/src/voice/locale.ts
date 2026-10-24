import type { Language } from '../types.ts';

export function recognitionLocale(language: Language): string {
  // Web Speech has no portable auto-detection; Hindi is the bilingual India fallback.
  return language === 'en' ? 'en-IN' : 'hi-IN';
}
export function spokenLanguage(language: Language, text: string): Language {
  if (language !== 'auto') return language;
  if (/[\u0900-\u097f]/.test(text)) return 'hi';
  const hindiWords = new Set(['hai', 'hain', 'ko', 'mujhe', 'papa', 'mummy', 'bukhar', 'saans', 'nahi', 'chahiye', 'ghar', 'dard', 'kya', 'aap', 'karein']);
  const words = new Set(text.toLowerCase().match(/[a-z]+/g) || []);
  return [...words].filter(word => hindiWords.has(word)).length >= 2 ? 'hinglish' : 'en';
}
