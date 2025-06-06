import { API_BASE_URL } from '@/lib/constants';
import { fetcher } from '@/lib/fetcher';
import { Machine } from '@/lib/types/machine';

import CriticalAlertSystem from './components/live-alert';
import LiveFeedWrapper from './components/live-feed-wrapper';
import PageHeader from './components/page-header';
import { getOrg } from '@/lib/auth/getOrg';

export default async function LiveFeed() {
  const {organization_uid} = await getOrg();

  const machines = await fetcher<{
    status: string;
    data: Machine[];
  }>(`${API_BASE_URL}/machines?organization_uid=${organization_uid}`);

  console.log(machines);

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader />
      <div className="h-full w-full overflow-hidden rounded-lg border">
        <LiveFeedWrapper machines={machines?.data ?? []} />
      </div>
      <CriticalAlertSystem enableSound={true} mockAlerts={true} />
    </section>
  );
}
