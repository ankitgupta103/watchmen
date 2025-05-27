import { getCookie } from '@/lib/cookies';
import { User } from '@/lib/types/user';

export default function useUser() {
  const user = JSON.parse(getCookie('user') || '{}') as User;

  return {
    user,
    organizations: user?.roles,
  };
}
