import React from 'react';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import { Machine } from '@/lib/types/machine';

export default function DeviceListing({ machines }: { machines: Machine[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Last Seen</TableHead>
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
            <TableCell>
              <Badge
                variant={
                  machine.data.status === 'online'
                    ? 'default'
                    : machine.data.status === 'offline'
                      ? 'destructive'
                      : 'secondary'
                }
                className="capitalize"
              >
                {machine.data.status}
              </Badge>
            </TableCell>
            <TableCell>
              {new Date(machine.data.lastSeen).toLocaleString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </TableCell>
            <TableCell>
              {machine.location.lat.toFixed(4)},{' '}
              {machine.location.lng.toFixed(4)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
