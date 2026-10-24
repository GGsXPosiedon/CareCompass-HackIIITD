import { caregivers } from '../data';
import { mockIntake } from './mock';
import { validateCaregivers, validateTriage } from './contracts';
import type { BookingRequest, Caregiver, IntakeRequest, TriageResponse } from '../types';

export const DEMO_MODE = !import.meta.env.VITE_API_BASE_URL;
const BASE = String(import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const delay = () => new Promise(resolve => setTimeout(resolve, 550));

async function request(path: string, body?: unknown): Promise<unknown> {
  const response = await fetch(`${BASE}${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    signal: AbortSignal.timeout(20000),
  });
  if (!response.ok) throw new Error('API_REQUEST_FAILED');
  return response.json();
}
export async function intake(payload: IntakeRequest): Promise<TriageResponse> {
  if (DEMO_MODE) { await delay(); return mockIntake(payload); }
  return validateTriage(await request('/triage', payload));
}
export async function getCaregivers(ids: string[]): Promise<Caregiver[]> {
  if (DEMO_MODE) { await delay(); return caregivers.filter(c => ids.includes(c.id)); }
  // Companion endpoint agreed with your backend team; never hydrate real matches with demo profiles.
  const data = await request(`/caregivers?ids=${encodeURIComponent(ids.join(','))}`);
  return validateCaregivers(data);
}
export async function createBooking(payload: BookingRequest): Promise<{ id: string }> {
  if (DEMO_MODE) { await delay(); return { id: `DEMO-${crypto.randomUUID().slice(0, 8).toUpperCase()}` }; }
  const result = await request('/bookings', payload) as { id?: unknown };
  if (!result || typeof result.id !== 'string' || !result.id) throw new Error('INVALID_BOOKING');
  return { id: result.id };
}
