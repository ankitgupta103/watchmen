import React, { Suspense } from 'react';

import AppSidebar from '@/components/common/app-sidebar';
import { SidebarProvider } from '@/components/ui/sidebar';
import { Skeleton } from '@/components/ui/skeleton';

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <Suspense
        fallback={
          <Skeleton className="bg-accent/50 h-screen w-[255px] animate-pulse" />
        }
      >
        <AppSidebar />
      </Suspense>
      <div className="h-screen w-full overflow-y-auto">{children}</div>
    </SidebarProvider>
  );
}
