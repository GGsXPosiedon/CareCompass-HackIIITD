# Sarvam voice input and output

CareCompass builds on GD Arena's short-recording → server transcription → generated speech pattern. The care microphone now opens a hands-free conversation that sends spoken turns, plays replies and listens again. The existing Python care backend is unchanged.

## Enable locally

1. Copy `frontend/.env.example` to `frontend/.env.local` if needed. Local environment files are ignored.
2. Set the **server-only** variable `SARVAM_API_KEY` to your Sarvam subscription key. Never use a `VITE_` prefix for a credential.
3. Keep the default matching models/voice, or configure compatible values:

   ```dotenv
   SARVAM_API_KEY=your_sarvam_key
   SARVAM_STT_MODEL=saaras:v3
   SARVAM_TTS_MODEL=bulbul:v3
   SARVAM_SPEAKER=ritu
   ```

4. Restart `npm run dev` and reload the browser. `/api/voice` should return `{"provider":"sarvam","maxSeconds":25}`. It never returns the key.
5. Press the microphone (**Start voice conversation**) on Find care and grant microphone access. Speak your care need, then pause. With Sarvam configured, about 1.25 seconds of quiet after speech ends a turn; **Done speaking** also submits it. Turns are capped at 25 seconds.
6. The app transcribes and sends the turn to the existing care backend, displays its question or recommendation, speaks it, then listens for your next answer. Your spoken transcript and voice controls appear inside the chat composer, with no floating panel. Full conversations remain available in Chat history. A follow-up answer retains the existing care conversation history.
7. **Speak now** interrupts a spoken reply and opens the microphone. **Pause** turns the microphone off; **Resume listening** continues. **End voice conversation**, Escape, navigating away or hiding the tab ends the session. No speech for 10 seconds pauses Sarvam capture instead of repeatedly sending silent requests.
8. Emergency guidance is spoken and stops the conversation loop. Use **View emergency guidance** to return to the emergency screen. Voice never books appointments or calls a number; use the existing caregiver and booking controls.

This is turn-based voice conversation over the current care API, not a new general-purpose assistant or simultaneous full-duplex audio. The microphone is off while a reply plays, so the assistant cannot hear itself. Use **Speak now** to interrupt. Browser speech is the fallback without a Sarvam key; its endpoint timing is controlled by browser recognition.

Typed care conversations stay silent until **Read aloud** is selected. Voice conversation mode speaks replies automatically; **Stop playback** remains available during manual playback. If a browser blocks audio, use the playback control once to enable it. Other existing dictation controls continue to insert editable text without automatically submitting it.

The Sarvam key covers speech input/output only. It does not enable Gemini or change the backend's care-routing model. No Sarvam key is included in the repository or browser bundle.

## Language behavior

| UI language mode | Sarvam STT language/mode | Speech output |
|---|---|---|
| English | `en-IN` / `transcribe` | `en-IN` |
| Hindi | `hi-IN` / `transcribe` | `hi-IN` |
| Hinglish | `hi-IN` / `translit` (Roman script) | `hi-IN`, including English words |
| Auto | `unknown` / `transcribe` | Hindi for Devanagari/Hinglish text; English otherwise |

In voice conversation mode, transcription is automatically submitted as a care request. Outside that mode, dictation only adds editable text to the input. The app transcribes speech rather than asking a generative model to invent a medical answer from audio.

## Routes and deployment

The frontend owns a small server-side adapter:

- `GET /api/voice`: provider availability, with no credentials.
- `POST /api/voice?action=transcribe&language=en|hi|hinglish|auto`: mono 16kHz PCM16 WAV → `{text, provider}`.
- `POST /api/voice?action=speak&language=…`: `{text}` → WAV audio bytes.

The browser calls only these same-origin routes. The adapter forwards validated requests to `https://api.sarvam.ai/speech-to-text` and `/text-to-speech` using the subscription header on the server. It does not send the key in a URL or expose Sarvam response bodies in errors.

**Vite dev/preview:** `server/voice-plugin.mjs` registers the voice route before the existing `/api` care-backend proxy. Both services use the same frontend origin, and no Python speech route is needed.

**Vercel Services:** use the repository root and its `vercel.json`. The specific `/api/voice` rewrite selects the frontend voice function before the general care API proxy rule. Set `SARVAM_API_KEY` and optional model/voice variables server-side. The care function separately calls the private backend through its runtime `BACKEND_URL` binding. See [the services deployment guide](../docs/DEPLOYMENT.md#vercel-services).

**Other/static hosts:** uploading only `dist` does not deploy the adapter. Host the voice function separately behind the same-origin `/api/voice` route. Without a working route/key, supported browsers use their speech APIs instead and identify browser voice as the fallback. The UI does not claim to use Sarvam when it is unavailable. In conversation mode, Sarvam failures pause the session with a retry control; typing remains available. Standalone read-aloud can fall back to browser speech with an explicit notice.

Microphone recording requires HTTPS or localhost and browser support for `getUserMedia`, `MediaRecorder` and Web Audio. Speech playback resumes audio from the user's click to support browsers that restrict autoplay.

## Limits and privacy

- Short clips only: nominally 25 seconds, mono PCM16 at 16kHz, maximum 1 MiB upload. Malformed WAV, overlong clips and texts above 2,500 characters are rejected.
- Silent audio is detected before a paid transcription call and returns an empty transcript.
- Only one recording or playback runs at a time. Navigation, language changes, hiding the tab and component cleanup stop active audio and abort pending voice requests.
- No recorded audio, transcription cache or generated speech is written to disk or persistent browser storage by this integration. Audio/text are sent to Sarvam when cloud voice is enabled; browser fallback may use the browser vendor's service. Use synthetic examples only.
- Same-origin/custom-header checks and bounded per-instance rate limits protect the prototype route. Public production use needs a deployment-wide quota/access policy; the in-memory limit is not a distributed security boundary.

## Verification

`npm test` includes WAV conversion, silence, language payloads, subscription-key isolation, provider failure handling, microphone track cleanup, navigation cancellation, and real local HTTP middleware tests against an injected Sarvam response. The provider mocks do not make paid calls.

The local `/api/voice` route, automatic reply playback, conversation start/pause/end, shared light/dark themes and 390px inline voice-composer layout were checked. Automated conversation tests cover turn order, interruption, silence, provider failure, emergency termination and ignoring late responses after End. **Live Sarvam recognition accuracy, real microphone capture and Sarvam audio quality are not claimed verified without a configured key and a spoken test on the target device.**

## Reference and attribution

- GD Arena [speech-to-text implementation](https://github.com/GGsXPosiedon/ps2-gd-arena/blob/ee9bee3e6d73899beba996373e8b8ca26076873d/src/lib/server/stt.ts) and [Sarvam voices](https://github.com/GGsXPosiedon/ps2-gd-arena/blob/ee9bee3e6d73899beba996373e8b8ca26076873d/src/lib/server/voices.ts), MIT, Copyright (c) 2026 Shubham Swami. CareCompass adapts the workflow, WAV/silence approach and language settings, with one care-assistant voice rather than GD Arena's participant voices.
- [Sarvam speech-to-text REST](https://docs.sarvam.ai/api-reference/speech-to-text/transcribe) and [text-to-speech REST](https://docs.sarvam.ai/api-reference/text-to-speech/convert).
- [Vercel Node.js Functions](https://vercel.com/docs/functions/runtimes/node-js).

### Preserving Hindi

New chats default to Auto. Auto sends Sarvam `language_code=unknown` with `mode=transcribe`; Hindi output is preserved in Devanagari. It does not call a speech-to-English translation route. Hindi/Hinglish text chooses Hindi playback. Explicit language choices remain available; older saved conversations retain their language, so choose Auto or Hindi if needed. Browser fallback uses Hindi recognition for Auto because Web Speech lacks a portable multi-language auto-detection setting. These paths have mocked regression coverage; live microphone recognition accuracy must still be checked on the demo device.
