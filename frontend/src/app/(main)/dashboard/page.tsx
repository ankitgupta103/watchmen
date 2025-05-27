import React from 'react';

import { mockMachines } from '@/lib/mock-data';

import DeviceListing from './components/device-listing';
import PageHeader from './components/page-header';

export default function DashboardPage() {
  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader />
      <div className="bg-background h-full w-full overflow-hidden rounded-lg border">
        <DeviceListing machines={mockMachines} />
      </div>
    </section>
  );
}
