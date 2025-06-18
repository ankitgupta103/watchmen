import { getOrg } from '@/lib/auth/getOrg';
import { API_BASE_URL } from '@/lib/constants';
import { fetcher } from '@/lib/fetcher';
import { Machine } from '@/lib/types/machine';

import DeviceDetailsClient from './components/device-details-client';

export default async function DeviceDetailsPage({
  params,
}: {
  params: Promise<{ deviceId: string }>;
}) {
  const { deviceId } = await params;
  const { organization_uid, organization_id } = await getOrg();

  const { data: machines } = await fetcher<{
    status: string;
    data: Machine[];
  }>(`${API_BASE_URL}/machines?organization_uid=${organization_uid}`);

  const device = machines.find((m) => m.id === Number(deviceId));
  if (!device) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <h2 className="mb-2 text-2xl font-bold">Device not found</h2>
        <p className="text-muted-foreground">
          No device matches the provided ID.
        </p>
      </div>
    );
  }

  return <DeviceDetailsClient device={device} orgId={organization_id} />;
}
