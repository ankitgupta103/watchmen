import { Badge } from '@/components/ui/badge';

import { Machine, MachineData } from '@/lib/types/machine';
import { cn, getStatusColor, getStatusText } from '@/lib/utils';

interface PopupContent {
  machine: Machine;
  machineData: MachineData;
  isOnline: boolean;
}

export default function PopupContent({
  machine,
  machineData,
  isOnline,
}: PopupContent) {
  return (
    <>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">{machine.name.toUpperCase()}</h3>
        <Badge
          variant={isOnline ? 'default' : 'destructive'}
          className="text-xs"
        >
          {isOnline ? 'Online' : 'Offline'}
        </Badge>
      </div>

      <div className="space-y-1 text-xs">
        <div>
          <strong>Machine ID:</strong> {machine.id}
        </div>

        {/* Status information */}
        <div className={cn('font-medium', getStatusColor(isOnline))}>
          <strong>Status:</strong>{' '}
          {getStatusText(isOnline, machineData.event_count)}
        </div>

        {/* Recent event activity indicator */}
        {machineData.is_pulsating && (
          <div className="mt-1 border-t pt-1 text-xs text-orange-600">
            <strong>🔔 Recent Event Activity</strong>
          </div>
        )}

        {/* Last event info */}
        {machineData.last_event && (
          <div className="mt-1 border-t pt-1 text-xs text-blue-600">
            <strong>Last Event:</strong> {machineData.last_event.eventstr}
            <br />
            <span className="text-gray-500">
              {new Date(machineData.last_event.timestamp).toLocaleTimeString()}
            </span>
          </div>
        )}

        <div className="mt-1 border-t pt-1 text-xs text-gray-500">
          <strong>Location:</strong> {machine?.last_location?.lat ?? '0.0000'},{' '}
          {machine?.last_location?.long ?? '0.0000'}
        </div>

        <div className="text-xs text-gray-400">Click to view details</div>
      </div>
    </>
  );
}
