import React from 'react';

import { mockMachines } from '@/lib/mock-data';

import HeatMapCalendar from './components/heat-map-calendar';
import PageHeader from './components/page-header';

export default function CalendarPage() {
  const machines = mockMachines;

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader />
      <div className="bg-background h-full w-full overflow-hidden rounded-lg border">
        <HeatMapCalendar machines={machines} />
      </div>
    </section>
  );
}
