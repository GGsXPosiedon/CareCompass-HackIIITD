import { handleCare } from './care-proxy.mjs';
import { handleVoice } from './sarvam.mjs';

// An explicit Node service: the Vite service only produces static assets.
export default {
  fetch(request) {
    return new URL(request.url).pathname === '/api/voice'
      ? handleVoice(request)
      : handleCare(request);
  },
};
