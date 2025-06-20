import { Info } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import { Machine } from '@/lib/types/machine';
import { formatBufferSize } from '@/lib/utils';
import { Separator } from '@/components/ui/separator';

const MachineInfoHeader = ({
  machine,
  bufferSize,
  mqttConnected,
}: {
  machine: Machine;
  bufferSize: number;
  mqttConnected: boolean;
}) => {
  const lastSeen = machine?.last_location?.timestamp
    ? new Date(machine.last_location.timestamp)
    : null;
  const oneHourAgo = new Date(Date.now() - 1000 * 60 * 60);
  const isOnline = !!lastSeen && lastSeen > oneHourAgo;

  return (
    <Card className="shadow flex flex-col gap-2">
      <CardHeader className="h-10">
        <CardTitle className="flex items-center gap-1 text-lg">
          <Info className="h-5 w-5" />
          Machine Information
        </CardTitle>
        <Separator />
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-3 flex-1" >
        <div>
          <span className="text-sm font-medium text-gray-500">Status</span>
          <div className="text-sm">
            <Badge variant={isOnline ? 'default' : 'destructive'}>
              {isOnline ? 'Online' : 'Offline'}
            </Badge>
          </div>
        </div>
        <div>
          <span className="text-sm font-medium text-gray-500">MQTT Status</span>
          <div className="text-sm">
            <Badge variant={mqttConnected ? 'default' : 'destructive'}>
              {mqttConnected ? 'Connected' : 'Disconnected'}
            </Badge>
          </div>
        </div>
        <div>
          <span className="text-sm font-medium text-gray-500">Location</span>
          <div className="text-sm">
            {machine.last_location?.lat ?? 'N/A'},{' '}
            {machine.last_location?.long ?? 'N/A'}
          </div>
        </div>
        <div>
          <span className="text-sm font-medium text-gray-500">Owner</span>
          <div className="text-sm">{machine.current_owner_name}</div>
        </div>
        <div>
          <span className="text-sm font-medium text-gray-500">Buffer Size</span>
          <div className="text-sm">{formatBufferSize(bufferSize)}</div>
        </div>
        <div>
          <span className="text-sm font-medium text-gray-500">Machine UID</span>
          <div className="font-mono text-sm">{machine.machine_uid}</div>
        </div>
      </CardContent>
    </Card>
  );
};

export default MachineInfoHeader;
