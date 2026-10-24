# Frontend verification

Current checkpoint: focused care entry with a dark conversational shell and serif headings, plus the secondary Roojh-inspired patient workspace.

## Focused care entry — 24 October 2026

- Full English browser journey exercised in the new shell: Fever & cough → Find the right care → age → No to the synthetic emergency question → recommendation → caregiver → remaining time → Confirm demo booking → confirmation → Download summary action → My bookings.
- New request preserves a completed booking in this tab. English/Hindi switching updates the care interface; the booking remains in history.
- Hindi sample submission reaches the Hindi age question from the new composer.
- Synthetic emergency input from the composer skips matching and booking and shows the 112 link. No call was placed.
- Mobile drawer opens, chooses a destination and closes; desktop sidebar can collapse/expand. The secondary family workspace opens and the primary care entry remains available.
- Entry inspected at 1440×900 and 390×844. Hindi input and follow-up checked at 320 pixels, with document scroll width equal to client width after correcting the body's minimum width. Tablet layout also inspected.
- Review captures are local working artifacts under `.impeccable/review/`. The full-page capture API produced an invalid desktop export despite correct DOM geometry; the native viewport capture was used and inspected for the desktop review.
- All 18 automated checks and the TypeScript/Vite production build pass. No real backend or microphone session was used. The summary download action was exercised; the downloaded file contents were not independently inspected.

## Automated

- `npm test`: 18 passing checks covering emergency priority, incomplete/conflicting responses, schema and ranking validation, multilingual emergency fixtures, follow-up progression, availability, past slots, family-profile isolation, dose-log deduplication, reading validation, assistant boundaries and reset factories.
- `npm run build`: TypeScript and Vite production build pass.

## Browser checks performed

- Core synthetic journey: intake, two follow-ups, care recommendation, ranked profiles, time selection, required-slot validation, booking confirmation and booking history.
- Emergency escalation during a Hindi follow-up; caregiver selection is bypassed and the 112 dialler link is visible. No emergency call was placed.
- Core connection-error fixture preserves the typed request. Outside-coverage fixture retains the same-day recommendation while showing no caregivers.
- Changing location from the empty result returns to intake.
- Core English/Hindi layouts inspected at 1440, 768 and 390 pixels; a 320-pixel overflow was corrected and rechecked.
- Workspace home inspected on desktop and at 390 pixels.
- Family switch → synthetic upload → briefcase; the added record appears only in the selected member's summary.
- Consent preview requires confirmation; access preview can be revoked. No real sharing was performed.
- Vitals chart/history render; entering a reading updates the selected profile.
- Medication marked taken appears in dose history.
- Scripted chat, ABHA consent preview, synthetic hospital-code linking, token creation/cancellation and local text messaging were exercised.
- Native Help dialog opens and closes with Escape.

## Verification limits

The real backend is absent. Live triage, actual appointments, authentication, ABHA/OTP, OCR, clinical review, real sharing, hospital systems and live AI are not verified or connected. Browser microphone/camera capture, speech quality, local PDF/media preview and file downloads should be manually checked on the target demonstration device. In-app reminder timing works only while this tab remains open; there is no background notification service.

The frontend design inspector could not launch its own browser in this environment (`spawn EPERM`), so visual checks used the connected in-app browser. The source design lint reported zero failures; its two warnings were intentional date zero-padding and the floating dialog's shadow.

The latest user-supplied ChatGPT screenshot and Claude-like type direction replace the earlier unselected generated landing-page concepts. The implemented landing screen is a working care intake, not a marketing page.
