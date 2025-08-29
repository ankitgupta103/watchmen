'use client';

import React from 'react';
import { MoreHorizontal, Plus, Tag } from 'lucide-react';

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
import LocationMap from './location-map';

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


  const formatUptime = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      return `${minutes}m`;
    } else {
      const hours = Math.floor(seconds / 3600);
      return `${hours}h`;
    }
  };

  const formatGpsStaleness = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      return `${minutes}m`;
    } else if (seconds < 86400) {
      const hours = Math.floor(seconds / 3600);
      return `${hours}h`;
    } else {
      const days = Math.floor(seconds / 86400);
      return `${days}d`;
    }
  };

  return (
    <TableRow key={machine.id}>
      <TableCell>{machine.id}</TableCell>
      <TableCell className="font-medium">{machine.name}</TableCell>
      {/* <TableCell>
        <Badge
          variant="outline"
          className={`border ${getConnectionStatusColor(machine.connection_status)}`}
        >
          {machine.connection_status}
        </Badge>
      </TableCell> */}
      <TableCell>
        <LocationMap 
          lat={machine.last_location?.lat} 
          long={machine.last_location?.long}
        />
      </TableCell>
      <TableCell>
        <TagDisplay
          tags={machine.tags}
          onDeleteTag={(tagId) => onDeleteTag(machine.id, tagId)}
          showDeleteButtons={true}
        />
      </TableCell>
      <TableCell>{machine?.specifications?.uptime ? formatUptime(machine.specifications.uptime) : '-'}</TableCell>
      <TableCell>{machine?.specifications?.photos_taken ? `${machine?.specifications?.photos_taken}` : '-'}</TableCell>
      <TableCell>{machine?.specifications?.events_seen ? `${machine?.specifications?.events_seen}` : '-'}</TableCell>
      <TableCell>{machine?.specifications?.gps_staleness ? formatGpsStaleness(machine.specifications.gps_staleness) : '-'}</TableCell>
      <TableCell>
        {machine?.specifications?.neighbours && machine.specifications.neighbours.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {machine.specifications.neighbours.map((neighbour, index) => (
              <Badge key={index} variant="secondary" className="text-xs">
                {neighbour}
              </Badge>
            ))}
          </div>
        ) : (
          '-'
        )}
      </TableCell>
      <TableCell>{machine?.specifications?.shortest_path ? `${machine?.specifications?.shortest_path}` : '-'}</TableCell>
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
            <DropdownMenuItem 
              onClick={() => onEditTags(machine)}
              disabled={!machine.tags || machine.tags.length === 0}
            >
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
