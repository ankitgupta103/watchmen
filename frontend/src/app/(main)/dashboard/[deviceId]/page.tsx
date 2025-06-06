import { mockMachines } from '@/lib/mock-data';

import DeviceDetailsClient from './components/device-details-client';

export default async function DeviceDetailsPage({
  params,
}: {
  params: Promise<{ deviceId: string }>;
}) {
  const { deviceId } = await params;

  const device = mockMachines.find((m) => m.id === Number(deviceId));
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
  return <DeviceDetailsClient device={device} />;
}
