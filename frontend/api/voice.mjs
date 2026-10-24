import { handleVoice } from '../server/sarvam.mjs';

export const maxDuration = 30;
export default { fetch: request => handleVoice(request) };
