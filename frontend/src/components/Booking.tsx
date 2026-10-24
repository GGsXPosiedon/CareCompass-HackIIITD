import { ArrowLeft, ArrowRight, CalendarDays, Check, Download, MapPin } from 'lucide-react';
import type { Copy } from '../i18n';
import { careLabel } from '../i18n';
import type { Booking as BookingType, Caregiver, CareType, Location } from '../types';
import { bookingSlots, formatDate, formatTime } from '../lib/flow';
import { DEMO_MODE } from '../lib/api';
import { BookingDates } from './BookingDates';
import { Avatar } from './Caregivers';
import { BookingSummary } from './Summary';

export function BookingForm({ copy, hindi, caregiver, careType, location, date, setDate, slot, setSlot, sameDay, busy, error, onRetry, onBack, onConfirm }: { copy: Copy; hindi: boolean; caregiver: Caregiver; careType: CareType; location: Location; date: string; setDate: (date: string) => void; slot: string; setSlot: (slot: string) => void; sameDay: boolean; busy: boolean; error: string; onBack: () => void; onConfirm: () => void; onRetry: () => void }) {
  const slots = bookingSlots(caregiver.slots, date);
  return <><button className="text-button back-button" disabled={busy} onClick={onBack}><ArrowLeft size={17} />{copy.back}</button><div className="page-heading"><h1 tabIndex={-1}>{copy.bookingTitle}</h1><p>{copy.bookingIntro}</p></div>
    <div className="care-grid"><section className="request-panel"><div className="booking-provider"><Avatar caregiver={caregiver} /><div><h2>{caregiver.name}</h2><p className="muted">{hindi ? caregiver.roleHi : caregiver.role}</p></div></div>
      <form onSubmit={e => { e.preventDefault(); onConfirm(); }}><BookingDates copy={copy} hindi={hindi} date={date} sameDay={sameDay} busy={busy} onChange={setDate}/>
        <fieldset className="booking-fieldset"><legend>{copy.slots}</legend><div className="slot-options">{slots.map(s => <button type="button" key={s} className={`slot-option ${slot === s ? 'chosen' : ''}`} aria-pressed={slot === s} onClick={() => setSlot(s)} disabled={busy}>{formatTime(s, hindi)}</button>)}</div>{busy ? <p role="status" className="muted">{copy.loadingAvailability}</p> : null}{!busy && !slots.length ? <p role="status" className="muted">{copy.noSlots}</p> : null}</fieldset>
        {error ? <p role="alert" className="error-message">{error}</p> : null}<button type="button" className="text-button" disabled={busy} onClick={onRetry}>{copy.refreshAvailability}</button>
        <button className="button primary full-width" disabled={busy || !slot || !slots.includes(slot)} type="submit">{busy ? <span className="spinner" aria-hidden="true" /> : null}{busy ? copy.bookingBusy : DEMO_MODE ? copy.confirmDemo : copy.confirmLive}{!busy ? <ArrowRight size={18} /> : null}</button>
        {DEMO_MODE ? <p className="small muted booking-note">{copy.bookingNote}</p> : null}
      </form>
    </section><BookingSummary copy={copy} hindi={hindi} caregiver={caregiver} careType={careType} date={date} slot={slot} location={location} /></div></>;
}
export function Confirmation({ copy, hindi, booking, onBookings, onNew }: { copy: Copy; hindi: boolean; booking: BookingType; onBookings: () => void; onNew: () => void }) {
  function download() {
    const text = [booking.demo ? copy.appointmentDemo : copy.appointment, `${copy.reference}: ${booking.id}`, `${copy.service}: ${careLabel(booking.careType, hindi)}`, `${copy.provider}: ${booking.caregiver.name}`, `${copy.date}: ${formatDate(booking.date, hindi)}`, `${copy.time}: ${formatTime(booking.slot, hindi)}`, `${copy.selectedLocation}: ${booking.location.label}`, booking.demo ? copy.confirmedDemoNote : ''].join('\n');
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `carecompass-${booking.id}.txt`; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <div className="confirmation"><div className="confirmation-check" aria-hidden="true"><Check size={30} /></div><div className="page-heading"><h1 tabIndex={-1}>{booking.demo ? copy.confirmedTitle : copy.confirmedLive}</h1><p>{copy.confirmedIntro}</p></div>{booking.demo ? <p className="confirmation-notice">{copy.confirmedDemoNote}</p> : null}
    <div className="confirmation-card"><div className="booking-provider"><Avatar caregiver={booking.caregiver} /><div><h2>{booking.caregiver.name}</h2><p className="muted">{careLabel(booking.careType, hindi)}</p></div></div><dl className="confirmation-details"><div><dt>{copy.date}</dt><dd>{formatDate(booking.date, hindi)}</dd></div><div><dt>{copy.time}</dt><dd>{formatTime(booking.slot, hindi)}</dd></div><div><dt>{copy.selectedLocation}</dt><dd>{booking.careType === 'teleconsultation' ? copy.online : booking.location.label}</dd></div><div><dt>{copy.reference}</dt><dd className="reference">{booking.id}</dd></div></dl></div>
    <div className="confirmation-actions"><button className="button primary" onClick={onBookings}>{copy.viewBookings}<ArrowRight size={18} /></button><button className="button secondary" onClick={download}><Download size={17} />{copy.download}</button></div><button className="text-button" onClick={onNew}>{copy.startOver}</button>
  </div>;
}
export function Bookings({ copy, hindi, bookings, onNew, onExploreServices }: { copy: Copy; hindi: boolean; bookings: BookingType[]; onNew: () => void; onExploreServices?: () => void }) {
  return <><div className="page-heading heading-with-action"><div><h1 tabIndex={-1}>{copy.bookingsTitle}</h1><p>{copy.bookingsIntro}</p></div>{bookings.length ? <button className="button primary" onClick={onNew}>{copy.findCare}<ArrowRight size={17} /></button> : null}</div>
    {onExploreServices ? <button className="button secondary bookings-explore" onClick={onExploreServices}>{hindi ? 'स्वास्थ्य सेवाएँ देखें' : 'Explore health services'}<ArrowRight size={17}/></button> : null}
    {!bookings.length ? <div className="empty-bookings"><CalendarDays size={35} strokeWidth={1.4} /><h2>{copy.emptyBookings}</h2><p>{copy.emptyBookingsBody}</p><button className="button primary" onClick={onNew}>{copy.findCare}<ArrowRight size={18} /></button></div> : <div className="bookings-list">{bookings.map(booking => <article className="past-booking" key={booking.id}><div className="booking-provider"><Avatar caregiver={booking.caregiver} /><div><h2>{booking.caregiver.name}</h2><p>{careLabel(booking.careType, hindi)}</p></div>{booking.demo ? <span className="status-pill neutral">{copy.appointmentDemo}</span> : null}</div><div className="past-booking-meta"><span><CalendarDays size={17} />{formatDate(booking.date, hindi)} · {formatTime(booking.slot, hindi)}</span><span><MapPin size={17} />{booking.careType === 'teleconsultation' ? copy.online : booking.location.label}</span></div><p className="small muted">{copy.reference}: {booking.id}</p></article>)}</div>}<p className="session-note">{copy.sessionNote}</p></>;
}
