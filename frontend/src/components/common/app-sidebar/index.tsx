'use client';

import dynamic from 'next/dynamic';

const Sidebar = dynamic(() => import('./sidebar'), {
  ssr: false,
});

export default function AppSidebar() {
  return <Sidebar />;
}
