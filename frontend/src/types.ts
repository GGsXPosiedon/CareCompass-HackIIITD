export type Language = 'en' | 'hi' | 'hinglish' | 'auto';
export type CareType = 'paramedic_home_visit' | 'nurse_home_visit' | 'gp_teleconsult' | 'specialist_consult' | 'emergency_referral';
export type Urgency = 'routine' | 'same_day' | 'immediate';
export interface Message { role: 'user' | 'assistant'; content: string }
export interface Location { lat: number; lng: number; label: string }
export interface IntakeRequest {
  user_input: string;
  language: Language;
  location: { lat: number; lng: number };
  conversation_history: Message[];
}
export interface Match { caregiver_id: string; score: number; reason: string }
export interface TriageResponse {
  follow_up_question: string | null;
  care_type: CareType | null;
  urgency: Urgency | null;
  red_flags: string[];
  reasoning: string;
  matched_caregivers: Match[];
  answer_options?: string[];
}
export interface Caregiver {
  id: string;
  name: string;
  initials: string;
  role: string;
  roleHi: string;
  careType: CareType;
  experience: number;
  distance: number;
  languages: string[];
  rating: number;
  reviews: number;
  skills: string[];
  skillsHi: string[];
  slots: string[];
  tint: string;
}
export interface Booking {
  id: string;
  caregiver: Caregiver;
  date: string;
  slot: string;
  location: Location;
  careType: CareType;
  demo: boolean;
}
export interface BookingRequest { caregiver_id: string; slot: string; date: string; location: { lat: number; lng: number } }
