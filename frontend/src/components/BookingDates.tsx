import { CalendarDays, Check } from 'lucide-react';
import type { Copy } from '../i18n';
import { bookingDate, formatDate } from '../lib/flow';

export function BookingDates({ copy, hindi, date, sameDay, busy, onChange }: {
  copy: Copy; hindi: boolean; date: string; sameDay: boolean; busy: boolean; onChange: (date: string) => void;
}) {
  const dates = sameDay ? [bookingDate()] : [bookingDate(), bookingDate(1)];
  return <fieldset className="booking-fieldset"><legend>{copy.date}</legend><div className="date-options">
    {dates.map((day, index) => <button key={day} type="button" className={`date-option ${date === day ? 'chosen' : ''}`} aria-pressed={date === day} onClick={() => onChange(day)} disabled={busy}>
      <CalendarDays size={18}/><span>{index === 0 ? copy.today : copy.tomorrow}<small>{formatDate(day, hindi)}</small></span>{date === day ? <Check size={17}/> : null}
    </button>)}
  </div><p className="small muted">{copy.serviceTime}</p></fieldset>;
}
