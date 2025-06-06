'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { API_BASE_URL, TOKEN_KEY } from '@/lib/constants';
import { deleteCookie, getCookie } from '@/lib/cookies';

export default function Logout() {
  const router = useRouter();

  useEffect(() => {
    async function handleLogout() {
      try {
        const token = getCookie(TOKEN_KEY);
        const sessionId = getCookie('sessionId');

        const headers: Record<string, string> = {
          Authorization: `Bearer ${token}`,
        };
        await fetch(`${API_BASE_URL}/auth/logout/`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({
            sessionId: sessionId,
          }),
        });
        deleteCookie(TOKEN_KEY);
        deleteCookie('organization');
        deleteCookie('sessionId');
        deleteCookie('expiry');
        deleteCookie('user');

        router.push('/auth/login');
      } catch (error) {
        console.error('Logout error:', error);
      }
    }
    handleLogout();
  }, [router]);

  return <div>Logging out...</div>;
}
