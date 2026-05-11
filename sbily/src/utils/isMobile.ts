declare global {
  interface Window {
    opera: string;
    MSStream: unknown;
  }
}

const ANDROID_PATTERN = /android/i;
const IOS_PATTERN = /ip(?:ad|hone|od)/i;
const IE_MOBILE_PATTERN = /iemobile/i;
const MOBILE_PATTERN = /mobile/i;

export function isMobile(): boolean {
  const userAgent: string =
    // eslint-disable-next-line node/no-unsupported-features/node-builtins
    navigator?.userAgent ?? navigator?.vendor ?? window?.opera ?? "";

  return (
    ANDROID_PATTERN.test(userAgent) ||
    (IOS_PATTERN.test(userAgent) && window.MSStream != null) ||
    IE_MOBILE_PATTERN.test(userAgent) ||
    MOBILE_PATTERN.test(userAgent)
  );
}
