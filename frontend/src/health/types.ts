export type HealthPage = 'home' | 'records' | 'summary' | 'vitals' | 'labs' | 'medications' | 'abha' | 'services' | 'messages' | 'settings' | 'care' | 'appointments';
export type RecordCategory = 'Lab report' | 'Prescription' | 'Radiology' | 'Cardiology' | 'Vaccination' | 'Consultation';
export interface HealthRecord { id: string; title: string; category: RecordCategory; date: string; source: string; status: 'Sample reviewed' | 'Awaiting extraction'; description: string; url?: string; fileType?: string; tags: string[] }
export type Metric = 'Blood pressure' | 'Blood glucose' | 'Heart rate' | 'Weight' | 'SpO2';
export interface Reading { id: string; metric: Metric; value: number; secondary?: number; date: string; time: string; note: string }
export interface Medication { id: string; name: string; instructions: string; time: string; startDate: string; endDate: string; active: boolean }
export interface DoseLog { id: string; medicationId: string; date: string; action: 'Taken' | 'Skipped'; time: string }
export interface ChatMessage { role: 'user' | 'assistant'; text: string; time: string; feedback?: 'helpful' | 'unhelpful' }
export interface Chat { id: string; title: string; messages: ChatMessage[] }
export interface AccessGrant { id: string; doctor: string; recordIds: string[]; expires: string; active: boolean }
export interface Hospital { id: string; name: string; area: string; services: string[] }
export interface HospitalToken { id: string; hospitalId: string; department: string; date: string; number: number; status: 'Requested' | 'Cancelled'; kind: 'Queue token' | 'Appointment' }
export interface HealthNotice { id: string; title: string; body: string; read: boolean; page: HealthPage }
export interface CareMessage { id: string; text: string; url?: string; type?: string }
export interface HealthState { records: HealthRecord[]; readings: Reading[]; medications: Medication[]; doses: DoseLog[]; chats: Chat[]; grants: AccessGrant[]; linkedHospitals: string[]; tokens: HospitalToken[]; notices: HealthNotice[]; careMessages: CareMessage[]; }
