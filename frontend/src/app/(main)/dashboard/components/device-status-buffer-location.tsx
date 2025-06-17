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

  console.log('sssssssssss',data);
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
      <TableCell>
        {data?.message?.location?.lat?.toFixed(4) ?? '-'},{' '}
        {data?.message?.location?.lng?.toFixed(4) ?? '-'}
      </TableCell>
    </>
  );
}
