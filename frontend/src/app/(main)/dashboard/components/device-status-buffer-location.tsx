'use client';

import React from 'react';
import { useMachineStats } from '@/hooks/use-machine-stats';

import { TableCell } from '@/components/ui/table';

import { formatBufferSize } from '@/lib/utils';

export default function DeviceBuffer({ machineId }: { machineId: number }) {
  const { buffer } = useMachineStats(machineId);

  return (
    <>
      <TableCell>{formatBufferSize(buffer)}</TableCell>
    </>
  );
}
