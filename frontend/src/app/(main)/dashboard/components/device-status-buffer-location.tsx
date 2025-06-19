'use client';

import React from 'react';
import { useMachineStats } from '@/hooks/use-machine-stats';

import { Badge } from '@/components/ui/badge';
import { TableCell } from '@/components/ui/table';

import { formatBufferSize } from '@/lib/utils';

export default function DeviceStatusBufferLocation({
  machineId,
}: {
  machineId: number;
}) {
  const { data, buffer } = useMachineStats(machineId);

  return (
    <>
      <TableCell>
        <Badge
          variant={
            data !== null
              ? 'default'
              : data === null
                ? 'destructive'
                : 'secondary'
          }
          className="capitalize"
        >
          {data !== null ? 'Online' : 'Offline'}
        </Badge>
      </TableCell>
      <TableCell>{formatBufferSize(buffer)}</TableCell>
    </>
  );
}
