import { mockMachines } from '@/lib/mock-data';

import LiveFeedWrapper from './components/live-feed-wrapper';
import PageHeader from './components/page-header';

export default function LiveFeed() {
  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader />
      <div className="h-full w-full overflow-hidden rounded-lg border">
        <LiveFeedWrapper machines={mockMachines} />
      </div>
    </section>
  );
}
