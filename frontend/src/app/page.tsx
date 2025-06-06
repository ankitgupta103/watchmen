'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { TOKEN_KEY } from '@/lib/constants';
import { getCookie } from '@/lib/cookies';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = getCookie(TOKEN_KEY);
    if (token) {
      router.push('/dashboard');
    } else {
      router.push('/auth/login');
    }
  }, [router]);

  return (
    <div className="grid h-screen w-screen place-items-center bg-gray-100">
      <h1>Home page</h1>
    </div>
  );
}
