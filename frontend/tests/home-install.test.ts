import test from 'node:test';
import assert from 'node:assert/strict';
import { dismissInstall, installDismissed, installGuide, requestInstall } from '../src/lib/home-install.ts';
import type { NativeInstallPrompt } from '../src/lib/home-install.ts';

test('home-screen guidance distinguishes Safari, other iPhone browsers and Android', () => {
  assert.equal(installGuide('iPhone Version/26.0 Mobile Safari/605.1'), 'ios-safari');
  assert.equal(installGuide('iPhone CriOS/140 Mobile Safari/605.1'), 'ios-browser');
  assert.equal(installGuide('Macintosh Version/26 Safari/605.1', 5), 'ios-safari');
  assert.equal(installGuide('Android Chrome/140 Mobile Safari/537.36'), 'browser');
});
test('install dismissal lasts seven days and storage failures do not break startup', () => {
  let value = '';
  dismissInstall({ setItem: (_key, next) => { value = next; } }, 1000);
  const storage = { getItem: () => value };
  assert.equal(installDismissed(storage, 1001), true);
  assert.equal(installDismissed(storage, 1000 + 7 * 86400000), false);
  assert.equal(installDismissed({ getItem: () => { throw new Error('blocked'); } }), false);
  assert.doesNotThrow(() => dismissInstall({ setItem: () => { throw new Error('blocked'); } }));
});
test('adding to home screen invokes the actual native prompt and respects the user choice', async () => {
  for (const outcome of ['accepted', 'dismissed'] as const) {
    let called = 0;
    const prompt = { prompt: async () => { called++; }, userChoice: Promise.resolve({ outcome }) } as NativeInstallPrompt;
    assert.equal(await requestInstall(prompt), outcome);
    assert.equal(called, 1);
  }
});
test('native install errors stay errors so the UI can offer browser instructions', async () => {
  const prompt = { prompt: async () => { throw new Error('unavailable'); }, userChoice: Promise.resolve({ outcome: 'dismissed' }) } as NativeInstallPrompt;
  await assert.rejects(requestInstall(prompt), /unavailable/);
});
