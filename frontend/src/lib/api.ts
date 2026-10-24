import { caregivers } from '../data';
import { mockIntake } from './mock';
import { validateCaregivers, validateTriage } from './contracts';
import type { BookingRequest, Caregiver, IntakeRequest, TriageResponse } from '../types';
import { createJsonRequest } from './http';

export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true';
const BASE = String(import.meta.env.VITE_API_BASE_URL || '/api');
const delay = () => new Promise(resolve => setTimeout(resolve, 550));

const request = createJsonRequest(BASE);
export async function intake(payload: IntakeRequest, signal?: AbortSignal): Promise<TriageResponse> {
  if (DEMO_MODE) { await delay(); signal?.throwIfAborted(); return mockIntake(payload); }
  return validateTriage(await request('/triage', payload, signal));
}
export async function getCaregivers(ids: string[], opts: { careType?: string | null; lat?: number; lng?: number; date?: string } = {}): Promise<Caregiver[]> {
  if (DEMO_MODE) { await delay(); return caregivers.filter(c => ids.includes(c.id)); }
  // Companion endpoint agreed with your backend team; never hydrate real matches with demo profiles.
  const q = new URLSearchParams({ ids: ids.join(',') });
  if (opts.careType) q.set('care_type', opts.careType);
  if (opts.lat !== undefined && opts.lng !== undefined && !(opts.lat === 0 && opts.lng === 0)) { q.set('lat', String(opts.lat)); q.set('lng', String(opts.lng)); }
  if (opts.date) q.set('date', opts.date);
  const data = await request(`/caregivers?${q}`);
  return validateCaregivers(data);
}
export async function createBooking(payload: BookingRequest): Promise<{ id: string }> {
  if (DEMO_MODE) { await delay(); return { id: `DEMO-${crypto.randomUUID().slice(0, 8).toUpperCase()}` }; }
  const result = await request('/bookings', payload) as { id?: unknown };
  if (!result || typeof result.id !== 'string' || !result.id) throw new Error('INVALID_BOOKING');
  return { id: result.id };
}
