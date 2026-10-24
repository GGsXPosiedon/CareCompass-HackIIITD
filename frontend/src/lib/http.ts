export class ApiError extends Error {
  readonly status: number;
  constructor(status: number) { super(`API_REQUEST_FAILED_${status}`); this.status = status; }
}

export function createJsonRequest(base: string, fetcher: typeof fetch = fetch) {
  return async (path: string, body?: unknown): Promise<unknown> => {
    const response = await fetcher(`${base.replace(/\/$/, '')}${path}`, {
      method: body === undefined ? 'GET' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      signal: AbortSignal.timeout(45000),
    });
    if (!response.ok) throw new ApiError(response.status);
    return response.json();
  };
}
