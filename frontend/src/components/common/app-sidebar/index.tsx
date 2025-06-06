'use client';

import dynamic from 'next/dynamic';

import { Skeleton } from '@/components/ui/skeleton';

const Sidebar = dynamic(() => import('./sidebar'), {
  ssr: false,
  loading: () => (
    <Skeleton className="bg-accent/50 h-screen w-[255px] animate-pulse" />
  ),
});

export default function AppSidebar() {
  return <Sidebar />;
}
