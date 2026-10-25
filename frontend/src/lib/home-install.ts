export type NativeInstallPrompt = Event & {
  prompt(): Promise<unknown>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
};

export type InstallGuide = 'ios-safari' | 'ios-browser' | 'browser';
export function installGuide(userAgent: string, touchPoints = 0): InstallGuide {
  const ios = /iPad|iPhone|iPod/i.test(userAgent) || (/Macintosh/i.test(userAgent) && touchPoints > 1);
  if (!ios) return 'browser';
  return /Safari/i.test(userAgent) && !/CriOS|FxiOS|EdgiOS|OPiOS/i.test(userAgent) ? 'ios-safari' : 'ios-browser';
}

export const INSTALL_DISMISS_KEY = 'carecompass.install.dismissedUntil';
export function installDismissed(storage: Pick<Storage, 'getItem'>, now = Date.now()): boolean {
  try { return Number(storage.getItem(INSTALL_DISMISS_KEY) || 0) > now; } catch { return false; }
}
export function dismissInstall(storage: Pick<Storage, 'setItem'>, now = Date.now()) {
  try { storage.setItem(INSTALL_DISMISS_KEY, String(now + 7 * 24 * 60 * 60 * 1000)); } catch { /* Dismissal still works in this tab. */ }
}
export async function requestInstall(prompt: NativeInstallPrompt) {
  await prompt.prompt();
  return (await prompt.userChoice).outcome;
}
