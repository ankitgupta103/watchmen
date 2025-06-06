import { TOKEN_KEY } from '@/lib/constants';
import { getCookie } from '@/lib/cookies';

export default function useToken() {
  const token = getCookie(TOKEN_KEY);

  return {
    token,
  } as {
    token: string | null;
  };
}
