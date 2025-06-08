import React from 'react';


import HeatMapCalendar from './components/heat-map-calendar';
import PageHeader from './components/page-header';
import { fetcher } from '@/lib/fetcher';
import { Machine } from '@/lib/types/machine';
import { API_BASE_URL } from '@/lib/constants';
import { getOrg } from '@/lib/auth/getOrg';

export default async function CalendarPage() {
  const {organization_id} = await getOrg();
  const machines = await fetcher<{
    status: string;
    data: Machine[];
  }>(`${API_BASE_URL}/machines?organization_uid=${organization_id}`);

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader />
      <div className="h-full w-full">
        <HeatMapCalendar machines={machines?.data ?? []} orgId={organization_id} />
      </div>
    </section>
  );
}