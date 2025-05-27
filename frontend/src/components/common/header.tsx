import React from 'react';

import { SidebarTrigger } from '../ui/sidebar';

export default function Header() {
  return (
    <header className="bg-background flex h-14 items-center gap-4 border-b px-4 lg:h-[60px] lg:px-6">
      <SidebarTrigger />
      <div className="flex-1">
        <h1 className="text-lg font-semibold">Dashboard</h1>
      </div>
    </header>
  );
}
