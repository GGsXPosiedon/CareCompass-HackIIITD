import { handleCare } from '../server/care-proxy.mjs';

export default { fetch: request => handleCare(request) };
