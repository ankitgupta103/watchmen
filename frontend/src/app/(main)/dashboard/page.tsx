import React from 'react';

import { getOrg } from '@/lib/auth/getOrg';
import { API_BASE_URL } from '@/lib/constants';
import { fetcher } from '@/lib/fetcher';
import { Machine, MachineTag } from '@/lib/types/machine';

import EventsFeed from './components/events-feed';
import PageHeader from './components/page-header';

export default async function DashboardPage() {
  const { organization_uid } = await getOrg();

  const { data: machines } = await fetcher<{ data: Machine[] }>(
    `${API_BASE_URL}/machines?organization_uid=${organization_uid}`,
  );

    const {data: allTags} = await fetcher<{data: MachineTag[]}>(
    `${API_BASE_URL}/tags?organization_uid=${organization_uid}`,
  );

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader />
      <div className="bg-background h-full w-full overflow-y-auto rounded-lg border">
        <EventsFeed machines={machines} allTags={allTags} />
      </div>
    </section>
  );
}
