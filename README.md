# CareCompass

A minimal, responsive patient-facing frontend for the Hack IIITD care-navigation challenge. The UI takes cues from Urban Company's service booking and Uber's request → selection → confirmation flow, while retaining its own teal-and-white identity. The expanded workspace follows Roojh's publicly documented patient workflow: choose a family profile → add records → organize the briefcase → review a summary → track readings and reminders → ask questions or connect to care.

## Roojh-inspired patient workspace

The app now opens on a family-health home, with these working frontend modules:

| Module | Implemented behavior |
| --- | --- |
| Family profiles | Add/edit fictional members, switch context, isolate records/readings/reminders/conversations and care bookings |
| Briefcase | Multiple local PDF/image selection, camera-input affordance, synthetic sample insertion, category/search/date sorting, document preview and metadata downloads |
| Consent preview | Select records, choose a fictional recipient and duration, create a local access preview and revoke it; no actual sharing |
| Health summary | Computed record/category totals, demographics, sample allergies, medication list, chronological care timeline, JSON download and a doctor-review request preview |
| Vitals | Blood pressure, glucose, heart rate, weight and SpO2 entry; 7/30/90-day history, trends, numeric validation and CSV export |
| Labs | Lab-category browsing and links to the profile's laboratory documents and recorded readings |
| Medications | Add/edit/pause/resume reminders, daily schedule, date range, mark taken/skipped and deduplicated dose history |
| Ask CareCompass | Profile-aware scripted conversations, history/resume/delete, feedback, optional speech input/output and transcript export |
| ABHA preview | Create/link consent flow using an intentionally invalid demo identity; unlink and download a clearly marked demo card |
| Health services | Synthetic hospitals and nearby-service discovery, sample QR-payload linking, hospital switching, appointment/token request previews, history and cancellation |
| Messages & updates | Read/unread activity, in-tab due-reminder notices, persistent per-profile local text/image/audio/video message previews |
| Settings | Data export, profile management, explicit integration limits and complete workspace reset |
| Care navigation | Original multilingual intake, triage-result display, emergency bypass, caregiver matching, booking and per-profile care-appointment history |

**These reproduce documented workflows as a local frontend demo, not exact feature parity with Roojh's private app.** Actual OCR/AI extraction, doctor verification, cloud health storage, authentication/OTP, real ABHA/ABDM, permission-enforced sharing, live AI, background notifications, hospital systems, subscriptions and payments are not connected or claimed. Profile data never receives a fake "doctor verified" status. File uploads say "Awaiting connected extraction" and no clinical values are invented from files. In-tab reminder checks run every 30 seconds only while the app remains open. Hospital codes and IDs are deliberately synthetic.

The public references used were [Roojh's patient page](https://roojh.com/for-patients/), the developer's [Google Play listing](https://play.google.com/store/apps/details?id=com.roojhproject.roojh), its published screenshots (family home, documents, labs and vitals), and [App Store release notes](https://apps.apple.com/in/app/roojh-health-care/id6444840591). Hospital-specific tokens and QR flows are documented in historical release notes; availability in every current Roojh account was not verified. No account was accessed, and no Roojh assets or proprietary code were copied. This app does not inherit Roojh's certifications or affiliations.

Health-workspace state lives in `frontend/src/health/Store.tsx`; its synthetic seed data is in `health/data.ts`. The existing care API adapter remains separate in `src/lib/api.ts`. No health files are sent to the care API. Local file object URLs are released when the workspace resets. Exported JSON excludes those object URLs and does not contain file bytes. Record-sharing and transcript-export controls do not contact recipients.

## Run locally

Requires **Node.js 24 LTS** (the native TypeScript Vite configuration requires Node 22.18+ or 24+).

```powershell
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173/**. On PowerShell systems that block npm.ps1, use `npm.cmd` in place of `npm`.

```powershell
npm test
npm run build
npm run preview
```

The production build is in `frontend/dist`. Serve it over HTTP; do not open its index.html directly from the file system. The app does not need backend services or API keys to run in demo mode. The patient workspace is always a synthetic local demo; `VITE_API_BASE_URL` only switches the care-navigation adapter.

## What is implemented

- Symptom intake with editable text, synthetic example prompts and patient-relation context.
- English and Hindi interface copy; English, Hindi, Hinglish and automatic language request modes.
- Browser speech recognition when supported, editable transcripts, text fallback, and optional read-aloud.
- One follow-up question at a time with server-supplied answer options and conversation history.
- Care type, urgency and explanations, followed by ranked caregiver cards and language filtering.
- Caregiver selection, available time slots, appointment review and demo confirmation.
- Session-only booking history and downloadable text summaries.
- Emergency escalation that bypasses follow-ups, matching and booking when a response contains red flags, immediate urgency or emergency referral.
- Empty availability, network failure, validation, disabled, loading and retry states.
- Mobile navigation, native accessible dialogs, keyboard focus, labels, live announcements and reduced-motion support.
- Locally bundled Instrument Sans and Noto Sans Devanagari; no external font requests.

## Important demo boundary

**This is a frontend prototype, not a clinical triage engine.** All cases, provider names, ratings, reviews, distances, availability and bookings are synthetic. `frontend/src/lib/mock.ts` deliberately returns preset outcomes to demonstrate screens. It is not a medically validated classifier, and arbitrary input must not be treated as assessed or safe.

Use only made-up examples. No real patient data should be entered. Requests and bookings are held in this tab's memory, with no localStorage or analytics. Refreshing clears them. Browser voice recognition may send audio to the browser vendor's service; do not speak real patient information.

The emergency button is a `tel:112` link and opens the device dialler only after a user selects it. It never calls automatically. The number is for India, verified against the [Government of India's Emergency Response Support System](https://112.gov.in/). Adapt emergency destinations before extending the demo to another country.

## Connect the team's backend

Copy `frontend/.env.example` to `frontend/.env.local`, set `VITE_API_BASE_URL`, and restart Vite. With a base URL set, the app stops using the synthetic API fixtures. It does **not** silently fall back to demo results on live API failures.

All network access is isolated in **`frontend/src/lib/api.ts`**. The triage contract comes from the problem statement, which explicitly says its final schema is still to be supplied. The profile and booking endpoints below are proposed integration contracts, not organiser-supplied APIs. Adapt this one file when the team finalises names and shapes.

### `POST /triage`

Request:

```json
{
  "user_input": "A family member: Papa ko do din se bukhar hai aur khansi bhi.",
  "language": "hinglish",
  "location": { "lat": 28.54, "lng": 77.27 },
  "conversation_history": []
}
```

The first input includes the selected patient relation as natural-language context. Later inputs contain the latest answer. Conversation history contains prior user/assistant messages as `{ "role": "user" | "assistant", "content": "..." }`. The current user input is not duplicated in history.

Response:

```json
{
  "follow_up_question": null,
  "care_type": "paramedic_home_visit",
  "urgency": "same_day",
  "red_flags": [],
  "reasoning": "Backend-provided plain-language explanation",
  "matched_caregivers": [
    { "caregiver_id": "CG_014", "score": 0.92, "reason": "Backend-provided matching reason" }
  ]
}
```

For follow-ups, return a non-empty `follow_up_question`, with `care_type` and `urgency` nullable. Optional `answer_options: string[]` supplies quick answers. The frontend never invents clinical follow-up questions in live mode. Return translated questions, reasons and answer options for the requested language.

Currently supported care-type values: `paramedic_home_visit`, `nurse_home_visit`, `gp_teleconsult`, `specialist_consult`, `emergency_referral`. Supported urgency: `routine`, `same_day`, `immediate`. Confirm these enums against the final care taxonomy. Responses are validated at runtime; invalid non-emergency output produces a retry error rather than a made-up recommendation.

Emergency fields are checked before normal-response validation, and caregiver matches are discarded on that path—even when the payload is incomplete or conflicting. The frontend does not independently diagnose symptoms. The backend owns clinically validated red-flag detection, negation handling, triage and ranking.

### `GET /caregivers?ids=CG_014%2CCG_022`

Returns a JSON array of complete profiles. See the **`Caregiver`** interface in `frontend/src/types.ts` and the synthetic examples in `frontend/src/data.ts`. Required fields:

```json
{
  "id": "CG_014",
  "name": "Aarav Mehta",
  "initials": "AM",
  "role": "Paramedic",
  "roleHi": "पैरामेडिक",
  "careType": "paramedic_home_visit",
  "experience": 6,
  "distance": 2.4,
  "languages": ["Hindi", "English"],
  "rating": 4.9,
  "reviews": 128,
  "skills": ["Home assessments"],
  "skillsHi": ["घर पर मूल्यांकन"],
  "slots": ["14:00", "16:30"],
  "tint": "sage"
}
```

Distances are kilometres, ratings are out of five, and slots use 24-hour `HH:mm` in the device's local time. The UI preserves triage ranking; it does not re-sort by rating. Missing or incompatible profiles block booking and show an error. Never hydrate live IDs from synthetic profiles.

The current demo reuses provider slot templates for today/tomorrow, filters past slots, and restricts same-day recommendations to today. Before real scheduling, replace this with backend-owned, date-specific slot IDs, a defined service timezone, and atomic availability validation.

### `POST /bookings`

```json
{
  "caregiver_id": "CG_014",
  "slot": "16:30",
  "date": "2026-10-24",
  "location": { "lat": 28.54, "lng": 77.27 }
}
```

Return `{ "id": "SERVER_BOOKING_REFERENCE" }` only after success. Confirmation never appears before this completes. The UI prevents duplicate in-flight submissions; production booking still needs server-side idempotency and slot reservation. A real backend also needs authentication, authorisation, input validation and an approved data-handling policy. No client-side API secrets belong in `VITE_*` variables.

Configure CORS to allow the frontend origin. Endpoint failures and 20-second timeouts leave the user's current answers intact. Location selection currently uses fixed synthetic demo areas; replace that control when a real service-area contract exists.

## Demo walkthrough

1. Open **Find care**, then choose **Fever & cough** (or switch to Hindi/Hinglish first).
2. Select **Find the right care**.
3. Answer the age question, then **No** to the synthetic emergency question.
4. Review the preset recommendation and open caregiver selection.
5. Choose a caregiver with remaining slots, choose a time, and confirm the **demo** booking.
6. View the confirmation, download the summary, and open **My bookings**.

The **Explore demo scenarios** disclosure shows emergency escalation, outside-coverage empty availability and a simulated connection error. These controls are absent when a backend URL is configured. Alternatively answer **Yes** or **Not sure** to the demo's emergency follow-up to test escalation mid-conversation.

## Structure

```text
frontend/
  src/
    App.tsx              # Original care-flow state and API orchestration
    health/              # Family workspace, records, summaries, vitals, reminders, chat and previews
    health.css           # Minimal workspace shell and responsive module styles
    components/          # Intake, questions, results, providers, booking, emergency, dialogs
    lib/api.ts           # Single network boundary and demo/live switch
    lib/contracts.ts     # Runtime response validation and emergency priority
    lib/mock.ts          # Scripted synthetic demo responses
    lib/flow.ts          # Routing and date/time helpers
    data.ts              # Synthetic providers, areas and examples
    i18n.ts              # English/Hindi interface copy and care labels
    types.ts             # Shared API and UI types
    styles.css           # Responsive visual system
  tests/flow.test.ts      # Safety, schema, fixture and scheduling checks
  tests/health.test.ts    # Profile isolation, dose history, readings, assistant and reset checks
```

## Validation and known limits

`npm test` covers red-flag priority, sparse/conflicting emergency payloads, malformed responses, invalid rankings and profiles, multilingual demo escalation, two-question intake, no availability and past-slot exclusion. `npm run build` checks TypeScript and generates the production bundle.

Browser QA covers the full synthetic booking flow, English/Hindi layouts at 1440, 768 and 390 pixels, emergency escalation during follow-up, booking validation/history, empty availability, location changes and the simulated failure state. See `frontend/QA.md` for the final verification notes.

Actual microphone capture, speech quality and permission-denial dialogs require manual verification on the target device. The real backend is not present in this repository and has not been validated. This frontend does not implement the team's model training, hidden-test prediction CSV, production dispatch, authentication, payments, or real medical decision support.

## Design and attribution

Design reference: [Urban Company](https://www.urbancompany.com/) for service clarity and [Uber](https://www.uber.com/in/en/) for the compact request/selection/confirmation pattern. No logos, photos, text or proprietary components from either site are used. The CareCompass mark is an original SVG; caregiver identities are initials, not stock doctor portraits.

React, Vite, TypeScript, Lucide icons and Fontsource fonts are declared in `frontend/package.json`; their licences remain with their packages. The app follows the Editorial greeting direction (seed `174117051`), adapted to a patient flow with sage surfaces and a custom care-journey rail. The dependency-free SVG chart helper in `frontend/public/health-charts.js` comes from the local frontend-design skill, with observer cleanup added. No model or external AI API is used by this frontend.
