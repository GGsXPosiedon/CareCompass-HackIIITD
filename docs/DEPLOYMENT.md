# Deployment

## Vercel Services (frontend, care API and voice)

Use the repository root as the Vercel project's **Root Directory**. The root `vercel.json` builds three services: `frontend` (Vite static pages), `gateway` (Node care proxy and voice), and `backend` (private FastAPI). The gateway explicitly uses `framework: node` with `server/gateway.mjs` as its entrypoint; it reuses the handlers in `frontend/server/`. Remove dashboard overrides for a frontend-only build/output directory; the service configuration owns those settings. There is no `frontend/vercel.json` in this setup.

Set `VITE_DEMO_MODE=false` and leave `VITE_API_BASE_URL` unset (or `/api`). `CARECOMPASS_API_TARGET` only affects ordinary Vite development/preview; it does not connect production care requests. Configure provider keys on the backend service, and optional `SARVAM_API_KEY` on the gateway service. Never put secrets in `VITE_*` variables. The `BACKEND_URL` service binding is injected into the gateway at runtime; do not hardcode it into the browser build.

Redeploy after changing the project root, environment or source. The previous deployment showed zero functions for the Vite service even though both frontend and backend builds succeeded; its API rewrites pointed at functions that were never emitted. The explicit Node gateway fixes that missing deployment artifact. After redeployment, the frontend may still show zero functions (it serves static assets), but the **gateway must show a Node function** and the backend must show its Python function. Deploying only `frontend/dist` is insufficient.

Run the smoke check after deployment (Node 24):

```sh
node deploy/check-services.mjs https://your-deployment.vercel.app
```

It checks public pages, JSON health/voice/caregivers responses, method restrictions and invalid POST validation without paid AI calls or reservations. `GET /api/triage` should return JSON with status **405**; `POST /api/triage` with an empty `user_input` should return **422**. A plain-text Vercel **404 NOT_FOUND** on `/api/triage`, `/api/health` and `/api/voice`, while `/care` loads, means the API handlers are not reachable: check the selected project root, deployed revision and generated functions before debugging model keys. The screenshot's public deployment exhibited this combination during diagnosis.

The top-level `/api/(.*)` rewrite now targets the gateway service directly, preserving URLs such as `/api/triage` and `/api/voice`. The gateway forwards only allowlisted care routes to the private backend. See [Vercel service routing](https://vercel.com/docs/services/routing).

### Request logs

Browser API failures appear in DevTools Console as `carecompass.api` with path, method, status, code, duration and server request ID. Missing routes display a deployment-specific error. Proxy logs appear in the gateway function's runtime logs as JSON (`care_proxy_request`); backend logs appear in the Python service logs. Search both by `request_id`, also returned as `X-Request-ID` and shown in failed chat replies when available. Proxy logs distinguish missing bindings, timeouts, unavailable backends, non-JSON responses and upstream HTTP errors. Platform 404s occur before these handlers and therefore have no application request ID.

Backend request logs include method, path, status, elapsed time and exception type/stack locations for unexpected failures. `LOG_LEVEL` defaults to `INFO`. These request diagnostics exclude bodies, query values, cookies, binding URLs and raw exception messages. The separate existing conversation failure recorder can store raw text: set `FAILURE_LOG=off` to disable it for hosted use.

## Same-server deployment

Use one public HTTPS domain. Caddy serves the built React files, strips `/api` before forwarding care requests to Python, and sends `/api/voice` to the Node voice adapter. The supplied configuration also serves `index.html` for direct links such as `/bookings`, `/settings` and `/chat/<id>`.

## Build and run

Example commands below assume a Linux server, Node 24 LTS, Python 3.12, uv and Caddy, with the project at `/srv/carecompass`. Adapt the path for your server. These are preparation instructions; no server has been deployed by this review.

1. Set `VITE_DEMO_MODE=false` and leave `VITE_API_BASE_URL` unset when building. Ensure any copied `frontend/.env` does not override these. Frontend environment settings are baked into the build.

   ```sh
   cd /srv/carecompass/frontend
   npm ci
   npm run build
   ```

2. Configure `backend/.env` with your server-side Gemini/provider keys. Keep `ROUTER_BACKEND=rules` and leave `ENCODER_PATH` and `INTENT_ENCODER_PATH` empty until the trained model is ready. Set `FAILURE_LOG=off` to disable raw conversation failure logs on the server.

   ```sh
   cd /srv/carecompass/backend
   uv sync --locked --no-dev
   uv run --no-sync uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
   ```

   **Use one worker/instance for this prototype.** Reservations are in process memory. Restarts erase them; multiple workers maintain different reservations and can double-book. Durable booking needs a shared database with a unique caregiver/date/slot constraint.

3. In a separate supervised process, start the voice adapter. Provide `SARVAM_API_KEY` and optional Sarvam model/speaker settings as server environment variables. This entry point does not load `frontend/.env`; export the settings or supply them through your process manager.

   ```sh
   cd /srv/carecompass/frontend
   export VOICE_PUBLIC_ORIGIN=https://care.example.com
   node server/voice-server.mjs
   ```

   `VOICE_PUBLIC_ORIGIN` must exactly match the public HTTPS origin, with no trailing slash. This preserves the same-origin check behind TLS termination. Without a Sarvam key, the adapter reports browser speech fallback.

4. Point your domain at the server, allow inbound ports 80/443, and configure Caddy. Give its service account read access to `frontend/dist`. Export these variables in Caddy's actual service environment:

   ```sh
   export CARECOMPASS_DOMAIN=care.example.com
   export CARECOMPASS_DIST=/srv/carecompass/frontend/dist
   caddy validate --config /srv/carecompass/deploy/Caddyfile --adapter caddyfile
   caddy run --config /srv/carecompass/deploy/Caddyfile --adapter caddyfile
   ```

Use your server's process manager to restart the Python, Node and Caddy processes after crashes/reboots. Keep ports 8000/3001 private. Serve only `frontend/dist`, never the repository root or environment files. Vite dev/preview is for local verification.

## Phone installation

The linked web manifest provides a standalone app launch at `/care`, 192/512 PNG icons, and an Apple touch icon. Settings includes English/Hindi instructions:

- Android Chrome: browser menu → Install app / Add to Home screen.
- iPhone Safari: Share → Add to Home Screen (enable Open as Web App if shown).

Install on the public HTTPS URL. Care requests and cloud voice still require internet. There is no offline cache or automatic install banner. Browser-menu installation in current Chrome does not require a service worker: [Chrome installation criteria](https://developer.chrome.com/blog/update-install-criteria). Physical-device installation and microphone behavior still need testing on the deployed domain.

## Review findings to keep in mind

- **In-memory booking and health state:** backend reservations disappear on restart; frontend documents and booking history disappear on refresh. Saved chats use localStorage and remain specific to that browser/origin. An installed app is not a user account or cross-device sync.
- **Public API access/cost:** Python triage/booking routes have no authentication or request quota. Anyone can invoke paid model calls or reserve slots. Voice has only per-process throttling. Restrict access or add an API quota before a public launch with paid keys.
- **Latency:** browser care requests stop after 45 seconds. Provider retries and sequential fallback chains can exceed that; server work can continue after the browser gives up. A proxy timeout increase alone does not fix this. Keep provider chains short and verify slow/failure cases against real providers.
- **Raw logs:** `backend/app/services/failure_log.py` logs user text and recent conversation history by default. Set `FAILURE_LOG=off` for the hosted demo unless retention is intentional.
- **Unbounded history strings:** turn count is capped at 40, but each `Turn.content` has no length limit. Bound total request body size at your gateway before broad public access.
- **Optional test dependency:** the base backend environment does not contain NumPy, yet `test_encoder_router.py` imports it unconditionally. Full test collection currently requires NumPy/encoder extras. Model training is outside this deployment pass.

## Deployment verification

Local review results: production frontend build passed; all 60 frontend tests passed (including HTTPS-origin voice checks); backend checks passed with 267 passed and 1 skipped after excluding `test_encoder_router.py`, which needs the missing optional NumPy dependency. The service notice appears only when a configured AI check fails; intentionally skipped checks and disabled providers do not show a failure banner. Patient profiles, selectors and saved-profile context have been removed. Legacy profile payloads are ignored and never sent to model providers. Manifest/icon dimensions and copied build assets were checked. Caddy is not installed locally, so its configuration still needs `caddy validate` on your server. Live provider calls and physical-device behavior were not tested.

- Open `/api/health`; check the expected classifier and configured LLM status. This is configuration/readiness information, not proof of a successful provider call.
- Refresh `/care`, `/bookings`, `/settings`, `/briefcase` and a saved chat URL directly. They must load the app.
- Check `/api/voice` returns JSON with the expected provider. Test a spoken turn over HTTPS on both target phone browsers.
- Send a synthetic care request, complete follow-ups, load caregivers and submit one booking. Verify a second reservation for the same slot receives 409.
- Check the manifest and all three icon URLs return their actual files. Install from the browser menu and launch from the home screen.
- Check environment-file URLs are inaccessible. Verify API responses are not cached.

References: [Caddy SPA/reverse-proxy patterns](https://caddyserver.com/docs/caddyfile/patterns), [FastAPI HTTPS deployment](https://fastapi.tiangolo.com/deployment/https/).
