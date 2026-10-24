# Frontend verification

Checkpoint: CareCompass core care flow plus the Roojh-inspired patient workspace.

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

Landing-page concepts are a later, separate task and are excluded from this checkpoint.
