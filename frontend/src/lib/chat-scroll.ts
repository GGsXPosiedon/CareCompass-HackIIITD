export interface ScrollPosition { scrollTop: number; scrollHeight: number; clientHeight: number }
export function isNearBottom(position: ScrollPosition, threshold = 80): boolean {
  return position.scrollHeight - position.clientHeight - Math.max(0, position.scrollTop) <= threshold;
}
