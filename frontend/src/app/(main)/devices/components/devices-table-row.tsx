'use client';

import React from 'react';
import { ArrowRight, MoreHorizontal, Plus, Tag } from 'lucide-react';

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

import LocationMap from './location-map';
import TagDisplay from './tag-display';

interface DevicesTableRowProps {
  machine: Machine;
  onDeleteTag: (machineId: number, tagId: number) => void;
  onAddTags: (machine: Machine) => void;
  onEditTags: (machine: Machine) => void;
  isEven?: boolean;
}

const DevicesTableRow: React.FC<DevicesTableRowProps> = ({
  machine,
  onDeleteTag,
  onAddTags,
  onEditTags,
  isEven = false,
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

  const renderShortestPath = (path: number[] | string) => {
    let machineIds: string[];

    if (Array.isArray(path)) {
      machineIds = path.map((id) => id.toString());
    } else {
      machineIds = path.split(',').map((id) => id.trim());
    }

    return (
      <div className="flex flex-wrap items-center gap-1">
        {machineIds.map((machineId, index) => (
          <React.Fragment key={index}>
            <span className="rounded bg-gray-100 px-2 py-1 font-mono text-sm">
              {machineId}
            </span>
            {index < machineIds.length - 1 && (
              <ArrowRight className="h-3 w-3 flex-shrink-0 text-gray-400" />
            )}
          </React.Fragment>
        ))}
      </div>
    );
  };

  return (
    <TableRow
      key={machine.id}
      className={`border-b border-gray-100 transition-colors duration-200 ${
        isEven
          ? 'bg-gray-25/30 hover:bg-gray-50/60'
          : 'bg-white hover:bg-gray-50/40'
      }`}
    >
      <TableCell className="font-mono text-sm text-gray-600">
        {machine.id}
      </TableCell>
      <TableCell className="font-semibold text-gray-900">
        {machine.name}
      </TableCell>
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
      <TableCell>
        <div className="flex items-center gap-2">
          {machine?.specifications?.uptime ? (
            <span className="font-medium">
              {formatUptime(machine.specifications.uptime)}
            </span>
          ) : (
            <span className="text-gray-400">-</span>
          )}
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          {machine?.specifications?.photos_taken ? (
            <span className="font-medium">
              {machine.specifications.photos_taken.toLocaleString()}
            </span>
          ) : (
            <span className="text-gray-400">-</span>
          )}
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          {machine?.specifications?.events_seen ? (
            <span className="font-medium">
              {machine.specifications.events_seen.toLocaleString()}
            </span>
          ) : (
            <span className="text-gray-400">-</span>
          )}
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          {machine?.specifications?.gps_staleness ? (
            <span className="font-medium">
              {formatGpsStaleness(machine.specifications.gps_staleness)}
            </span>
          ) : (
            <span className="text-gray-400">-</span>
          )}
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          {machine?.specifications?.neighbours &&
          machine.specifications.neighbours.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {machine.specifications.neighbours.map((neighbour, index) => (
                <Badge key={index} variant="secondary" className="text-xs">
                  {neighbour}
                </Badge>
              ))}
            </div>
          ) : (
            <span className="text-gray-400">-</span>
          )}
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          {machine?.specifications?.shortest_path ? (
            renderShortestPath(machine.specifications.shortest_path)
          ) : (
            <span className="text-gray-400">-</span>
          )}
        </div>
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
