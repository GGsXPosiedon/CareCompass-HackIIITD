# Sarvam voice input and output

CareCompass follows GD Arena's short-recording → server transcription → editable text pattern, with server-generated audio that plays automatically after each new assistant response. The existing Python care backend is unchanged.

## Enable locally

1. Open `frontend/.env.local` (git-ignored; a blank template is prepared locally). If it does not exist after cloning, copy `.env.example` to `.env.local`.
2. Set the **server-only** variable `SARVAM_API_KEY` to your Sarvam subscription key. Never use a `VITE_` prefix for a credential.
3. Keep the default matching models/voice, or configure compatible values:

   ```dotenv
   SARVAM_API_KEY=your_sarvam_key
   SARVAM_STT_MODEL=saaras:v3
   SARVAM_TTS_MODEL=bulbul:v3
   SARVAM_SPEAKER=ritu
   ```

4. Restart `npm run dev` and reload the browser. `/api/voice` should return `{"provider":"sarvam","maxSeconds":25}`. It never returns the key.
5. Use **Speak instead**, grant microphone access, speak for up to 25 seconds and press Stop. Check/edit the resulting text before sending it through the care flow. Recording stops automatically at the limit.
6. Send your message or answer. Each new assistant question, recommendation or emergency response plays automatically using Sarvam when configured (browser speech otherwise). Press **Stop playback** to interrupt it. Sending another answer, recording, changing pages or hiding the tab stops playback. Reopening an old response does not replay it. If your browser blocks automatic audio, press **Read aloud** once to enable playback; it also remains available for replay.

The Sarvam key covers speech input/output only. It does not enable Gemini or change the backend's care-routing model. No Sarvam key is included in the repository or browser bundle.

## Language behavior

| UI language mode | Sarvam STT language/mode | Speech output |
|---|---|---|
| English | `en-IN` / `transcribe` | `en-IN` |
| Hindi | `hi-IN` / `transcribe` | `hi-IN` |
| Hinglish | `hi-IN` / `translit` (Roman script) | `hi-IN`, including English words |
| Auto | `unknown` / `transcribe` | Hindi for Devanagari text; English otherwise |

The transcription is added to the input; it is never automatically submitted as a health request. The app transcribes speech rather than asking a generative model to invent a medical answer from audio.

## Routes and deployment

The frontend owns a small server-side adapter:

- `GET /api/voice`: provider availability, with no credentials.
- `POST /api/voice?action=transcribe&language=en|hi|hinglish|auto`: mono 16kHz PCM16 WAV → `{text, provider}`.
- `POST /api/voice?action=speak&language=…`: `{text}` → WAV audio bytes.

The browser calls only these same-origin routes. The adapter forwards validated requests to `https://api.sarvam.ai/speech-to-text` and `/text-to-speech` using the subscription header on the server. It does not send the key in a URL or expose Sarvam response bodies in errors.

**Vite dev/preview:** `server/voice-plugin.mjs` registers the voice route before the existing `/api` care-backend proxy. Both services use the same frontend origin, and no Python speech route is needed.

**Vercel:** deploy with **Root Directory `frontend`**. `api/voice.mjs` serves the same adapter as a Node function. Set `SARVAM_API_KEY` and optional model/voice variables in the project's server environment, then redeploy. Keep `/api/voice` out of any catch-all rewrite to the care backend. Care API hosting remains configured separately as described in [README.md](README.md).

**Other/static hosts:** uploading only `dist` does not deploy the adapter. Host the voice function separately behind the same-origin `/api/voice` route. Without a working route/key, supported browsers use their speech APIs instead and identify browser voice as the fallback. The UI does not claim to use Sarvam when it is unavailable. Sarvam playback failures also show an explicit browser-fallback notice; transcription failures leave typing available.

Microphone recording requires HTTPS or localhost and browser support for `getUserMedia`, `MediaRecorder` and Web Audio. Speech playback resumes audio from the user's click to support browsers that restrict autoplay.

## Limits and privacy

- Short clips only: nominally 25 seconds, mono PCM16 at 16kHz, maximum 1 MiB upload. Malformed WAV, overlong clips and texts above 2,500 characters are rejected.
- Silent audio is detected before a paid transcription call and returns an empty transcript.
- Only one recording or playback runs at a time. Navigation, language changes, hiding the tab and component cleanup stop active audio and abort pending voice requests.
- No recorded audio, transcription cache or generated speech is written to disk or persistent browser storage by this integration. Audio/text are sent to Sarvam when cloud voice is enabled; browser fallback may use the browser vendor's service. Use synthetic examples only.
- Same-origin/custom-header checks and bounded per-instance rate limits protect the prototype route. Public production use needs a deployment-wide quota/access policy; the in-memory limit is not a distributed security boundary.

## Verification

`npm test` includes WAV conversion, silence, language payloads, subscription-key isolation, provider failure handling, microphone track cleanup, navigation cancellation, and real local HTTP middleware tests against an injected Sarvam response. The provider mocks do not make paid calls.

The local `/api/voice` route, browser fallback Read aloud/Stop, theme consistency, and 390px mobile layout were checked. **Live Sarvam recognition accuracy, real microphone capture and Sarvam audio quality are not claimed verified without a configured key and a spoken test on the target device.**

## Reference and attribution

- GD Arena [speech-to-text implementation](https://github.com/GGsXPosiedon/ps2-gd-arena/blob/ee9bee3e6d73899beba996373e8b8ca26076873d/src/lib/server/stt.ts) and [Sarvam voices](https://github.com/GGsXPosiedon/ps2-gd-arena/blob/ee9bee3e6d73899beba996373e8b8ca26076873d/src/lib/server/voices.ts), MIT, Copyright (c) 2026 Shubham Swami. CareCompass adapts the workflow, WAV/silence approach and language settings, with one care-assistant voice rather than GD Arena's participant voices.
- [Sarvam speech-to-text REST](https://docs.sarvam.ai/api-reference/speech-to-text/transcribe) and [text-to-speech REST](https://docs.sarvam.ai/api-reference/text-to-speech/convert).
- [Vercel Node.js Functions](https://vercel.com/docs/functions/runtimes/node-js).
