'use client';

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

// Types
interface MachineTag {
  id: number;
  name: string;
  description?: string;
  color?: string;
}

interface MachineLocation {
  lat: number;
  long: number;
}

interface Machine {
  id: number;
  name: string;
  type: string;
  created_at: string;
  updated_at: string;
  last_location?: MachineLocation;
  tags?: MachineTag[];
  is_online?: boolean;
  last_seen?: string;
}

interface DeviceListingProps {
  machines: Machine[];
}

// Utility functions
const isMachineOnline = (machine: Machine): boolean => {
  if (machine.is_online !== undefined) {
    return machine.is_online;
  }
  
  if (!machine.last_seen) {
    return false;
  }
  
  const lastSeen = new Date(machine.last_seen);
  const now = new Date();
  const diffInMinutes = (now.getTime() - lastSeen.getTime()) / (1000 * 60);
  
  // Consider machine online if last seen within 5 minutes
  return diffInMinutes <= 5;
};

const formatBufferSize = (bytes?: number): string => {
  if (!bytes || bytes === 0) return '0 B';
  
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

// Device Buffer Component
function DeviceBuffer({ machineId }: { machineId: number }) {
  // This would typically use a hook to fetch buffer data
  // For now, returning a placeholder
  console.log('machineId', machineId);
  const buffer = 0; // Replace with actual buffer data from your hook
  
  return <TableCell>{formatBufferSize(buffer)}</TableCell>;
}

// Tag Display Component
function TagDisplay({ tags }: { tags: MachineTag[] }) {
  if (!tags || tags.length === 0) {
    return <div className="text-sm text-gray-500">No tags</div>;
  }

  return (
    <div className="flex flex-wrap gap-1">
      {tags.slice(0, 3).map((tag) => (
        <Badge key={tag.id} variant="outline" className="text-xs">
          {tag.name}
        </Badge>
      ))}
      {tags.length > 3 && (
        <Badge variant="outline" className="text-xs">
          +{tags.length - 3} more
        </Badge>
      )}
    </div>
  );
}

export default function DeviceListing({ machines }: DeviceListingProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Buffer</TableHead>
          <TableHead>Tags</TableHead>
          <TableHead>Location</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {machines.map((machine) => (
          <TableRow key={machine.id}>
            <TableCell className="font-medium">
              <Link 
                href={`/dashboard/${machine.id}`} 
                className="text-blue-600 hover:text-blue-800 hover:underline"
              >
                {machine.name}
              </Link>
            </TableCell>
            <TableCell className="capitalize">
              {machine.type.replace(/_/g, ' ')}
            </TableCell>
            <TableCell>
              <Badge
                variant={isMachineOnline(machine) ? 'default' : 'destructive'}
                className="capitalize"
              >
                {isMachineOnline(machine) ? 'Online' : 'Offline'}
              </Badge>
            </TableCell>
            <DeviceBuffer machineId={machine.id} />
            <TableCell>
              <TagDisplay tags={machine.tags || []} />
            </TableCell>
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