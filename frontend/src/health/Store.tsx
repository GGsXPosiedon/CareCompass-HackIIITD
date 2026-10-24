import { createContext, useContext, useEffect, useRef, useState } from 'react';
import type { Dispatch, ReactNode, SetStateAction } from 'react';
import { initialHealthState } from './data';
import type { HealthState } from './types';
interface Context { state: HealthState; setState: Dispatch<SetStateAction<HealthState>>; reset: () => void; registerUrl: (url: string) => void; version: number }
const HealthContext = createContext<Context | null>(null);
export function HealthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState(initialHealthState);
  const [version, setVersion] = useState(0);
  const urls = useRef<string[]>([]);
  function release() { urls.current.forEach(url => URL.revokeObjectURL(url)); urls.current = []; }
  useEffect(() => () => release(), []);
  function reset() { release(); setState(initialHealthState()); setVersion(v=>v+1); }
  return <HealthContext.Provider value={{ state, setState, reset, registerUrl: url => urls.current.push(url), version }}>{children}</HealthContext.Provider>;
}
export function useHealth() { const value = useContext(HealthContext); if (!value) throw new Error('Missing health provider'); return value; }
