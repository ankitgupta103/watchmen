interface CookieOptions {
  days?: number;
  path?: string;
  domain?: string;
  secure?: boolean;
  samesite?: 'Strict' | 'Lax' | 'None';
  maxAge?: number;
}

interface DeleteCookieOptions {
  path?: string;
  domain?: string;
}

export function getCookie(name: string): string | undefined {
  if (typeof document === 'undefined') return undefined;
  const nameEQ = name + '=';
  const ca = document?.cookie?.split(';');
  if (!ca) return undefined;
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) === ' ') {
      c = c.substring(1, c.length);
    }
    if (c.indexOf(nameEQ) === 0) {
      const value = c.substring(nameEQ.length, c.length);
      try {
        return decodeURIComponent(value);
      } catch (e) {
        console.error(`Error decoding cookie "${name}":`, e);
        return value;
      }
    }
  }
  return undefined;
}

export function setCookie(
  name: string,
  value: string,
  options: CookieOptions = {},
) {
  const encodedName = encodeURIComponent(name);
  const encodedValue = encodeURIComponent(value);

  let cookieString = `${encodedName}=${encodedValue}`;

  const path = options.path ?? '/';
  cookieString += `; path=${path}`;

  if (options.domain) {
    cookieString += `; domain=${options.domain}`;
  }

  let maxAgeSeconds: number | undefined = options.maxAge;
  if (maxAgeSeconds === undefined && options.days !== undefined) {
    maxAgeSeconds = options.days * 24 * 60 * 60;
  }

  if (maxAgeSeconds !== undefined) {
    cookieString += `; max-age=${Math.max(0, maxAgeSeconds)}`;

    const expiresDate = new Date();
    expiresDate.setTime(expiresDate.getTime() + maxAgeSeconds * 1000);
    cookieString += `; expires=${expiresDate.toUTCString()}`;
  }

  const secure =
    options.secure ?? (typeof window !== 'undefined' && window.isSecureContext);
  if (secure || options.samesite === 'None') {
    cookieString += `; Secure`;
  }

  const samesite = options.samesite ?? 'Lax';
  cookieString += `; SameSite=${samesite}`;

  document.cookie = cookieString;
}

export function deleteCookie(name: string, options: DeleteCookieOptions = {}) {
  setCookie(name, '', {
    path: options.path ?? '/',
    domain: options.domain,
    maxAge: 0,
  });
}
