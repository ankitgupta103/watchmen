'use client';

import React from 'react';
import Link from 'next/link';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import { Machine } from '@/lib/types/machine';

import DeviceStatusBufferLocation from './device-status-buffer-location';

export default function DeviceListing({ machines }: { machines: Machine[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Buffer</TableHead>
          <TableHead>Location</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {machines.map((machine) => (
          <TableRow key={machine.id}>
            <TableCell className="font-medium">
              <Link href={`/dashboard/${machine.id}`} key={machine.id}>
                {machine.name}
              </Link>
            </TableCell>
            <TableCell>{machine.type.replace(/_/g, ' ')}</TableCell>
            <DeviceStatusBufferLocation machineId={machine.id} />
            <TableCell>
              {machine?.last_location?.lat ?? '-'},{' '}
              {machine?.last_location?.long ?? '-'}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
