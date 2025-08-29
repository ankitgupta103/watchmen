import React from 'react';

import { getOrg } from '@/lib/auth/getOrg';
import { API_BASE_URL } from '@/lib/constants';
import { fetcher } from '@/lib/fetcher';
import { Machine } from '@/lib/types/machine';

import DevicesTable from './components/devices-table';
import PageHeader from './components/page-header';

export const revalidate = 60;

export default async function DevicesPage() {
  const { organization_uid } = await getOrg();

  const { data: machines } = await fetcher<{ data: Machine[] }>(
    `${API_BASE_URL}/machines?organization_uid=${organization_uid}`,
  );

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader />
      <div className="bg-background h-full w-full overflow-y-auto rounded-lg border p-6">
        {machines.length === 0 ? (
          <div className="flex h-32 items-center justify-center">
            <div className="text-muted-foreground">No machines found.</div>
          </div>
        ) : (
          <DevicesTable machines={machines} />
        )}
      </div>
    </section>
  );
}
