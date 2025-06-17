import { getOrg } from '@/lib/auth/getOrg';
import { API_BASE_URL } from '@/lib/constants';
import { fetcher } from '@/lib/fetcher';
import { Machine } from '@/lib/types/machine';

// import CriticalAlertSystem from './components/live-alert';
import LiveFeedWrapper from './components/live-feed-wrapper';
import PageHeader from './components/page-header';

export default async function LiveFeed() {
  const { organization_uid } = await getOrg();

  const { data: machines } = await fetcher<{
    status: string;
    data: Machine[];
  }>(`${API_BASE_URL}/machines?organization_uid=${organization_uid}`);

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader />
      <div className="h-full w-full overflow-hidden rounded-lg border">
        <LiveFeedWrapper machines={machines ?? []} />
      </div>
      {/* <CriticalAlertSystem enableSound={true} mockAlerts={true} /> */}
    </section>
  );
}
