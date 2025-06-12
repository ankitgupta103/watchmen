import React from 'react';

import { getOrg } from '@/lib/auth/getOrg';
import { API_BASE_URL } from '@/lib/constants';
import { fetcher } from '@/lib/fetcher';
import { Machine } from '@/lib/types/machine';

import DeviceListing from './components/device-listing';
import PageHeader from './components/page-header';

export default async function DashboardPage() {
  const { organization_uid } = await getOrg();

  const { data: machines } = await fetcher<{
    status: string;
    data: Machine[];
  }>(`${API_BASE_URL}/machine?organization_uid=${organization_uid}`);
  
  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader />
      <div className="bg-background h-full w-full overflow-hidden rounded-lg border">
        <DeviceListing machines={machines ?? []} />
      </div>
    </section>
  );
}
