'use client';

import { Camera, Loader2 } from 'lucide-react';
import Image from 'next/image';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface S3EventData {
  image_c_key: string;
  image_f_key: string;
  eventstr: string;
  timestamp?: string | Date;
  machineId?: number;
}

interface ProcessedEvent extends S3EventData {
  id: string;
  machineId: number;
  timestamp: string | Date;
  croppedImageUrl?: string;
  fullImageUrl?: string;
  imagesFetched: boolean;
  fetchingImages: boolean;
}

const EventsTable = ({
  events,
  onViewDetails,
}: {
  events: ProcessedEvent[];
  onViewDetails: (event: ProcessedEvent) => void;
}) => (
  <Table>
    <TableHeader>
      <TableRow>
        <TableHead>Timestamp</TableHead>
        <TableHead>Event</TableHead>
        <TableHead>Images</TableHead>
        <TableHead>Actions</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      {events.map((event) => (
        <TableRow key={event.id}>
          <TableCell>
            {new Date(event.timestamp).toLocaleString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </TableCell>
          <TableCell>
            <Badge variant="outline">{event?.eventstr || 'N/A'}</Badge>
          </TableCell>
          <TableCell>
            {event.fetchingImages ? (
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-gray-500">Loading...</span>
              </div>
            ) : event.imagesFetched ? (
              <div className="flex gap-2">
                {event.croppedImageUrl && (
                  <Image
                    src={event.croppedImageUrl}
                    alt="Cropped"
                    width={40}
                    height={40}
                    className="h-40 w-40 rounded border object-cover"
                  />
                )}
                {event.fullImageUrl && (
                  <Image
                    src={event.fullImageUrl}
                    alt="Full"
                    width={40}
                    height={40}
                    className="h-40 w-fit rounded border object-contain"
                  />
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Camera className="h-4 w-4 text-gray-400" />
                <span className="text-sm text-gray-500">Available</span>
              </div>
            )}
          </TableCell>
          <TableCell>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onViewDetails(event)}
            >
              View Details
            </Button>
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
);

export default EventsTable;
