export const pagePaths = {
  care: '/care', bookings: '/bookings', briefcase: '/briefcase', services: '/services', profile: '/profile', history: '/history', settings: '/settings',
} as const;
export type Page = keyof typeof pagePaths;
export interface Route { page: Page | 'not-found'; conversationId?: string }
export function resolveRoute(pathname: string): Route {
  const path = pathname.replace(/\/+$/, '') || '/';
  if (path === '/') return { page: 'care' };
  for (const [page, url] of Object.entries(pagePaths)) if (path === url) return { page: page as Page };
  const chat = /^\/chat\/([^/]+)$/.exec(path);
  if (chat) {
    try { return { page: 'care', conversationId: decodeURIComponent(chat[1]) }; } catch { /* Invalid URL. */ }
  }
  return { page: 'not-found' };
}
export function conversationPath(id: string): string { return `/chat/${encodeURIComponent(id)}`; }
export function parentPath(pathname: string, activeId?: string | null): string {
  const page = resolveRoute(pathname).page;
  if (page === 'profile') return pagePaths.settings;
  if (page === 'services') return pagePaths.bookings;
  return activeId ? conversationPath(activeId) : pagePaths.care;
}
