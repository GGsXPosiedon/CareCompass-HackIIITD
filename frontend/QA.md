# Frontend verification

Current checkpoint: three main destinations (Find care, My bookings and Briefcase), a shared dark/light theme, and health services reached from My bookings. The old family-workspace page and removed profile/account sections are absent.

## Navigation and theme verification

- Desktop and mobile menus show Find care, My bookings and Briefcase. Briefcase groups Home, Records, Health summary and Labs, with no second sidebar or header.
- Briefcase Home → Add health records opens the upload dialog. Inserting a synthetic record updated the summary count from three to four.
- My bookings → Explore health services opens the service directory; Back to my bookings returns correctly.
- Full fever journey completed in light mode through age, emergency follow-up, recommendation, caregiver and time selection. Switching to dark mode preserved the selected time; confirmation succeeded and the booking remained after visiting Briefcase and returning.
- Theme changes preserve the typed care request. Records, care, bookings, services and their dialogs share the selected mode. Upload dialog colors were checked in both modes.
- Dark/light desktop layouts inspected at 1440px and mobile at 390px. The theme control and booking view also fit at 320px; document width equals client width, with no horizontal overflow.
- Dark booking text contrast was checked from computed DOM colors. Browser microphone capture, actual uploaded file bytes and backend services were not exercised.

The following sections are historical verification records from preceding checkpoints; removed features are not part of the current UI.

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
