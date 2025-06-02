'use client';

import { useState } from 'react';
import Image from 'next/image';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import { Machine } from '@/lib/types/machine';

import PageHeader from './page-header';

export default function DeviceDetailsClient({ device }: { device: Machine }) {
  const [openEventIdx, setOpenEventIdx] = useState<number | null>(null);

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader deviceId={device.id.toString()} />
      {/* Device Info */}
      <div className="bg-background flex flex-col gap-4 rounded-lg border p-6 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="mb-1 text-3xl font-bold">
              {device.name.replace(/-/g, ' ')}
            </h1>
            <div className="mb-2 flex items-center gap-2">
              <Badge variant="secondary" className="capitalize">
                {device.type.replace(/_/g, ' ')}
              </Badge>
              <Badge
                variant={
                  device.data.status === 'online'
                    ? 'default'
                    : device.data.status === 'offline'
                      ? 'destructive'
                      : 'secondary'
                }
                className="capitalize"
              >
                {device.data.status}
              </Badge>
            </div>
            <div className="text-muted-foreground text-sm">
              Last seen:{' '}
              {new Date(device.data.lastSeen).toLocaleString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </div>
            <div className="text-muted-foreground text-sm">
              Location: {device.location.lat.toFixed(4)},{' '}
              {device.location.lng.toFixed(4)}
            </div>
          </div>
        </div>
      </div>
      {/* Suspicious Events */}
      <div className="bg-background rounded-lg border p-6 shadow-sm">
        <h2 className="mb-4 text-xl font-semibold">Suspicious Events</h2>
        {device.data.suspiciousEvents &&
        device.data.suspiciousEvents.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Marked</TableHead>
                <TableHead>Timestamp</TableHead>
                <TableHead>Image</TableHead>
                <TableHead>Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {device.data.suspiciousEvents.map((event, idx) => (
                <TableRow key={idx}>
                  <TableCell className="capitalize">
                    {event.type.replace(/_/g, ' ')}
                  </TableCell>
                  <TableCell>{(event.confidence * 100).toFixed(1)}%</TableCell>
                  <TableCell className="capitalize">{event.marked}</TableCell>
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
                    {event.url ? (
                      <Image
                        src={event.url}
                        alt="event"
                        className="h-14 w-20 rounded border object-cover"
                        width={100}
                        height={100}
                      />
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Dialog
                      open={openEventIdx === idx}
                      onOpenChange={(open) =>
                        setOpenEventIdx(open ? idx : null)
                      }
                    >
                      <Button
                        variant="outline"
                        onClick={() => setOpenEventIdx(idx)}
                      >
                        View
                      </Button>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Suspicious Event Details</DialogTitle>
                          <DialogDescription>
                            Detailed information for this suspicious event.
                          </DialogDescription>
                        </DialogHeader>
                        <div className="mt-2 flex flex-col gap-2">
                          <div>
                            <span className="font-semibold">Type:</span>{' '}
                            {event.type.replace(/_/g, ' ')}
                          </div>
                          <div>
                            <span className="font-semibold">Confidence:</span>{' '}
                            {(event.confidence * 100).toFixed(1)}%
                          </div>
                          <div>
                            <span className="font-semibold">Marked:</span>{' '}
                            {event.marked}
                          </div>
                          <div>
                            <span className="font-semibold">Timestamp:</span>{' '}
                            {new Date(event.timestamp).toLocaleString('en-US', {
                              month: 'long',
                              day: 'numeric',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </div>
                          {event.url && (
                            <div>
                              <span className="font-semibold">Image:</span>
                              <div className="mt-1">
                                <Image
                                  src={event.url}
                                  alt="event"
                                  width={300}
                                  height={200}
                                  className="rounded border object-cover"
                                />
                              </div>
                            </div>
                          )}
                        </div>
                        <DialogClose asChild>
                          <Button
                            onClick={() => setOpenEventIdx(null)}
                            className="hover:bg-primary/90"
                          >
                            Close
                          </Button>
                        </DialogClose>
                      </DialogContent>
                    </Dialog>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="text-muted-foreground">
            No suspicious events recorded.
          </div>
        )}
      </div>
      {/* Health Events */}
      <div className="bg-background rounded-lg border p-6 shadow-sm">
        <h2 className="mb-4 text-xl font-semibold">Health Events</h2>
        {device.data.healthEvents && device.data.healthEvents.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Timestamp</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {device.data.healthEvents.map((event, idx) => (
                <TableRow key={idx}>
                  <TableCell className="capitalize">
                    {event.type.replace(/_/g, ' ')}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        event.severity === 'critical'
                          ? 'destructive'
                          : event.severity === 'high'
                            ? 'secondary'
                            : 'default'
                      }
                      className="capitalize"
                    >
                      {event.severity}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {new Date(event.timestamp).toLocaleString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="text-muted-foreground">
            No health events recorded.
          </div>
        )}
      </div>
    </section>
  );
}
