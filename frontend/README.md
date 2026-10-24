# CareCompass

A minimal, responsive patient-facing frontend for the Hack IIITD care-navigation challenge. The app opens directly into a conversational care request: describe the need → answer follow-ups → review a recommendation → choose a caregiver and time → confirm a demo booking. The dark, spacious layout follows the user's ChatGPT screenshot, with locally bundled Lora serif headings inspired by Claude's typographic feel. CareCompass retains its own name and compass mark.

## Start here: find care

The header's sun/moon button switches the **entire app** between dark and light mode. Find care, My bookings, Briefcase, health services, inputs and dialogs always share the selected mode. Dark mode is the initial state; the current choice is retained while navigating in this tab. No patient data is written to local storage.

Open **Find care**, then choose **Fever & cough** (or switch to Hindi/Hinglish first).

1. Select **Find the right care**, which appears in the composer after a message is entered. You can also press Enter; Shift+Enter adds a new line.
2. Answer the age question and select **Continue**. Then choose **No** for the synthetic emergency question and select **Continue** again.
3. Review the preset recommendation and select **See available caregivers**.
4. Choose a caregiver with remaining slots, select **Choose a time**, pick a time and select **Confirm demo booking**.
5. View the confirmation, select **Download summary**, then open **My bookings**.

The microphone opens **Start voice conversation**, a hands-free care conversation with an on-screen transcript and typing fallback. The sidebar contains **Find care**, **My bookings**, **Briefcase** and **New request**. **My bookings** includes **Explore health services**. On mobile, open the menu to reach them. A new request keeps completed bookings in this tab; refreshing clears them.

## Voice conversation

1. Open **Find care**, press the microphone (**Start voice conversation**) and grant microphone access.
2. Speak your care need, then pause. Sarvam capture ends a turn after about 1.25 seconds of quiet following speech, or when you press **Done speaking**. Each turn is capped at 25 seconds.
3. The app transcribes and submits the turn to the existing care backend, shows its question or recommendation, speaks the reply, then listens for your next answer. Follow-up answers retain the current care conversation history.
4. Use **Speak now** to interrupt playback, **Pause / Resume listening** to control capture, or **End voice conversation** to return to the page. Escape, navigation and hiding the tab also end the session. Ten seconds without speech pauses Sarvam capture.
5. Review the recommendation and use the existing caregiver and booking controls on screen. Emergency guidance ends the voice loop; calls and bookings require manual action.

The panel includes a transcript and listening, transcribing, thinking, speaking and paused states in both themes. The microphone is off during spoken replies. This is turn-based conversation through the current care API; Sarvam supplies speech rather than the care answers. Supported browsers provide speech fallback when no Sarvam key is configured. Speech-provider failures pause the session with a retry control.

Typed conversations retain automatic reply playback with **Stop playback** and **Read aloud** controls. Full key setup, language behavior and hosting instructions are in [VOICE.md](VOICE.md). Live Sarvam recognition accuracy and audio quality need a configured key and a microphone test on the target device.

## Briefcase and health services

The main sidebar has three destinations: **Find care**, **My bookings**, and **Briefcase**. The chat-first landing layout and fonts are retained, with one shared dark/light theme across all sections.

**Briefcase** opens the document list directly. Its internal navigation contains **Home**, **Records**, **Health summary**, and **Labs**. Home provides record upload and recent documents; Records includes local PDF/image selection, camera-input affordance, sample insertion, search, category/date sorting, document previews, consent previews and metadata downloads. Health summary organizes the current synthetic patient's records and timeline; Labs links categories to documents and the lab-upload workflow.

**My bookings → Explore health services** opens the fictional hospital/service directory, hospital linking, request/token previews and their cancellation/history. It has a return action to My bookings. These previews do not contact hospitals, reserve queue positions or create real appointments.

The family-workspace page and its separate sidebar/header have been removed. Family profiles, ABHA preview, Messages & updates, Workspace settings and Care appointments are no longer app sections. The earlier assistant, profile-management, ABHA, messaging, settings and reminder UI files have been removed. Seed data and internal record-isolation helpers remain for synthetic fixtures and tests; no profile-management UI is exposed.

The record and hospital flows take inspiration from Roojh's documented patient experience. This is a local frontend demonstration, with no OCR, clinical verification, authentication, government integration, real sharing, live AI, payments or hospital backend. Record uploads and document URLs stay in this tab; object URLs are released when the application unmounts. State survives navigation between Briefcase, services and care booking, but clears on refresh.

Health state is provided once around the app in `src/health/Store.tsx`. `src/health/Briefcase.tsx` owns the four internal sections; `src/health/Services.tsx` is reached only from My bookings. The care API adapter remains separate in `src/lib/api.ts` and never receives Briefcase files.

## Run locally

Sarvam conversational voice and reply-playback setup is documented in [VOICE.md](VOICE.md). The subscription key stays server-side; the Python care backend does not need speech changes.

**To activate Sarvam:** add `SARVAM_API_KEY` to the prepared, git-ignored `frontend/.env.local`, restart the frontend, and reload.

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

The production build is in `frontend/dist`. Serve it over HTTP; do not open its index.html directly from the file system. Care navigation uses the existing backend by default. Vite dev and preview proxy `/api/*` to `http://127.0.0.1:8000/*`. Start the backend separately using the team's [backend instructions](../backend/README.md). Briefcase and health services remain synthetic local previews.

For an offline UI demonstration, explicitly set `VITE_DEMO_MODE=true` in `.env.local` and restart Vite. API failures never activate demo mode automatically. Gemini keys belong only in the backend's git-ignored environment file.

## What is implemented

- Symptom intake with editable text, synthetic example prompts and patient-relation context.
- English and Hindi interface copy; English, Hindi, Hinglish and automatic language request modes.
- Hands-free Sarvam voice conversations when configured: automatic spoken turns, replies, transcript, interruption, pause/resume, explicit browser-voice fallback and typing support.
- One follow-up question at a time with server-supplied answer options and conversation history.
- Care type, urgency and explanations, followed by ranked caregiver cards and language filtering.
- Caregiver selection, available time slots, appointment review and demo confirmation.
- Session-only booking history and downloadable text summaries.
- Emergency escalation that bypasses follow-ups, matching and booking when a response contains red flags, immediate urgency or emergency referral.
- Empty availability, network failure, validation, disabled, loading and retry states.
- Mobile navigation, native accessible dialogs, keyboard focus, labels, live announcements and reduced-motion support.
- Locally bundled Lora, Instrument Sans and Noto Sans Devanagari; no external font requests.

## Important demo boundary

**This is a frontend prototype, not a clinical triage engine.** All cases, provider names, ratings, reviews, distances, availability and bookings are synthetic. `frontend/src/lib/mock.ts` deliberately returns preset outcomes to demonstrate screens. It is not a medically validated classifier, and arbitrary input must not be treated as assessed or safe.

Use only made-up examples. No real patient data should be entered. Requests and bookings are held in this tab's memory, with no localStorage or analytics. Refreshing clears them. Configured Sarvam voice sends recorded audio and spoken-reply text to Sarvam; browser fallback may use the browser vendor's speech service. See [VOICE.md](VOICE.md).

The emergency button is a `tel:112` link and opens the device dialler only after a user selects it. It never calls automatically. The number is for India, verified against the [Government of India's Emergency Response Support System](https://112.gov.in/). Adapt emergency destinations before extending the demo to another country.

## Connect the team's backend

No frontend environment file is needed for the default local connection. Start the existing API on port 8000 and run the frontend on port 5173. To change the local API address, copy `.env.example` to `.env.local`, set `CARECOMPASS_API_TARGET`, and restart Vite. To call a deployed API directly, set `VITE_API_BASE_URL` to its base URL and keep `VITE_DEMO_MODE=false`.

For a deployed static frontend, configure the host to reverse-proxy `/api/*` to the backend root, or set `VITE_API_BASE_URL` **before building** and configure backend CORS. Vite's dev/preview proxy is not bundled into `dist`.

The adapter is in **`src/lib/api.ts`**; **`src/lib/http.ts`** preserves HTTP status codes for conflict recovery. These endpoints are already implemented by the team's backend. Confirm the final organiser schema separately before evaluation.

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

Supported care-type values: `paramedic_home_visit`, `home_nursing`, `lab_test_home`, `teleconsultation`, `emergency_112`. Supported urgency: `scheduled`, `same_day`, `emergency`. Responses are validated at runtime; invalid non-emergency output produces a retry error rather than a made-up recommendation.

Emergency fields are checked before normal-response validation, and caregiver matches are discarded on that path—even when the payload is incomplete or conflicting. The frontend does not independently diagnose symptoms. The backend owns clinically validated red-flag detection, negation handling, triage and ranking.

### `GET /caregivers?ids=CG_014%2CCG_022&care_type=home_nursing&date=2026-10-25`

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

Distances are kilometres, ratings are out of five, and slots use 24-hour `HH:mm` in **Asia/Kolkata (IST)**, matching the existing backend. Requests include `lat` and `lng` when location is known. The UI preserves triage ranking. Missing or incompatible profiles block booking and show an error. Live IDs are never hydrated from synthetic profiles.

Scheduled recommendations initially load tomorrow; same-day recommendations load today and cannot be moved to tomorrow. Both caregiver selection and booking request fresh profiles for the selected date. Date changes clear the selected time; loading and failed refreshes block confirmation. Entering booking refreshes availability again. `Refresh availability` retries a failed request. Only explicit offline demo mode reuses synthetic slot templates.

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

HTTP 409 clears the selected time, refreshes that date's slots, and asks the user to choose again; bookings are never retried automatically. Endpoint failures and 45-second timeouts preserve the user's request. The local proxy avoids cross-origin calls; a directly configured remote API requires CORS. Location selection still uses fixed synthetic demo areas.

## Demo walkthrough

Follow the **Start here: find care** steps above. The landing screen starts this same care-navigation flow; it does not route the request through the separate scripted health-record assistant.

The **Explore demo scenarios** disclosure shows emergency escalation, outside-coverage empty availability and a simulated connection error. These controls are absent when a backend URL is configured. Alternatively answer **Yes** or **Not sure** to the demo's emergency follow-up to test escalation mid-conversation.

## Structure

```text
frontend/
  src/
    App.tsx              # Original care-flow state and API orchestration
    CareShell.tsx        # Three-destination sidebar, shared health state and services access
    care-shell.css       # Chat-first shell, navigation and responsive layout
    themes.css           # Shared dark/light tokens for every section and dialog
    health/              # Briefcase, records, health summaries, labs, services and synthetic state
    health.css           # Light record/service module styles
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

`npm test` currently passes **51 checks**, including voice turn sequencing, silence, interruption, capture/playback cleanup, emergency termination, late-reply cancellation, and red-flag priority, sparse/conflicting emergency payloads, malformed responses, invalid rankings and profiles, multilingual demo escalation, two-question intake, no availability and past-slot exclusion. `npm run build` checks TypeScript and generates the production bundle.

Browser QA covers the full synthetic booking flow, English/Hindi layouts at 1440, 768 and 390 pixels, emergency escalation during follow-up, booking validation/history, empty availability, location changes and the simulated failure state. See `frontend/QA.md` for the final verification notes.

Actual microphone capture, speech quality and permission-denial dialogs require manual verification on the target device. The real backend is not present in this repository and has not been validated. This frontend does not implement the team's model training, hidden-test prediction CSV, production dispatch, authentication, payments, or real medical decision support.

## Design and attribution

Design reference: [Urban Company](https://www.urbancompany.com/) for service clarity and [Uber](https://www.uber.com/in/en/) for the compact request/selection/confirmation pattern. No logos, photos, text or proprietary components from either site are used. The CareCompass mark is an original SVG; caregiver identities are initials, not stock doctor portraits.

React, Vite, TypeScript, Lucide icons and Fontsource fonts are declared in `frontend/package.json`; their licences remain with their packages. The app follows the Editorial greeting direction (seed `174117051`), adapted to a patient flow with sage surfaces and a custom care-journey rail. The dependency-free SVG chart helper in `frontend/public/health-charts.js` comes from the local frontend-design skill, with observer cleanup added. No model or external AI API is used by this frontend.
