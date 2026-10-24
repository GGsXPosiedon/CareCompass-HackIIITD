// Keep one context unlocked by the send gesture across asynchronous responses.
let playbackContext: AudioContext | null = null;
export function primeVoicePlayback(): AudioContext | null {
  try {
    if (!playbackContext || playbackContext.state === 'closed') {
      playbackContext = typeof window.AudioContext === 'function' ? new window.AudioContext() : null;
    }
    if (playbackContext?.state === 'suspended') void playbackContext.resume().catch(() => {});
    return playbackContext;
  } catch { return null; }
}
export function voicePlaybackContext() { return playbackContext; }

const spokenResponses = new WeakSet<object>();
// Defer the claim so React StrictMode's discarded effect cannot consume it.
export function scheduleResponseVoice(response: object, play: () => void): () => void {
  let cancelled = false;
  queueMicrotask(() => {
    if (cancelled || spokenResponses.has(response)) return;
    spokenResponses.add(response);
    play();
  });
  return () => { cancelled = true; };
}
