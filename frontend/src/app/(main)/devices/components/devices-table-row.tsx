'use client';

import React from 'react';
import { MapPin, MoreHorizontal, Plus, Tag } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { TableCell, TableRow } from '@/components/ui/table';

import { Machine } from '@/lib/types/machine';

import TagDisplay from './tag-display';

interface DevicesTableRowProps {
  machine: Machine;
  onDeleteTag: (machineId: number, tagId: number) => void;
  onAddTags: (machine: Machine) => void;
  onEditTags: (machine: Machine) => void;
}

const DevicesTableRow: React.FC<DevicesTableRowProps> = ({
  machine,
  onDeleteTag,
  onAddTags,
  onEditTags,
}) => {
  const getConnectionStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'offline':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'connecting':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const formatLocation = (location: {
    lat: number;
    long: number;
    timestamp: string;
  }) => {
    return `${location?.lat}, ${location?.long}`;
  };

  return (
    <TableRow key={machine.id}>
      <TableCell className="font-medium">{machine.name}</TableCell>
      <TableCell>{machine.type}</TableCell>
      <TableCell>
        <Badge
          variant="outline"
          className={`border ${getConnectionStatusColor(machine.connection_status)}`}
        >
          {machine.connection_status}
        </Badge>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <MapPin className="text-muted-foreground h-4 w-4" />
          <span className="text-sm">
            {formatLocation(machine.last_location)}
          </span>
        </div>
      </TableCell>
      <TableCell>
        <TagDisplay
          tags={machine.tags}
          onDeleteTag={(tagId) => onDeleteTag(machine.id, tagId)}
          showDeleteButtons={true}
        />
      </TableCell>
      <TableCell>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <span className="sr-only">Open menu</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onAddTags(machine)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Tags
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onEditTags(machine)}>
              <Tag className="mr-2 h-4 w-4" />
              Edit Tags
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
};

export default DevicesTableRow;
