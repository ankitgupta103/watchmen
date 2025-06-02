'use client'

import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import { mockMachines } from '@/lib/mock-data';
import Image from 'next/image';
import PageHeader from './components/page-header';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from '@/components/ui/dialog';
import { useState } from 'react';
import { Button } from '@/components/ui/button';

export default function DeviceDetailsPage({
  params,
}: {
  params: { deviceId: string };
}) {
  const device = mockMachines.find((m) => m.id === Number(params.deviceId));
  // openEventIdx: { type: 'suspicious' | 'health', idx: number } | null
  const [openEvent, setOpenEvent] = useState<
    | { type: 'suspicious'; idx: number }
    | { type: 'health'; idx: number }
    | null
  >(null);

  if (!device) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <h2 className="mb-2 text-2xl font-bold">Device not found</h2>
        <p className="text-muted-foreground">
          No device matches the provided ID.
        </p>
      </div>
    );
  }

  const suspiciousEvent =
    openEvent?.type === 'suspicious' && openEvent.idx >= 0
      ? device.data.suspiciousEvents?.[openEvent.idx]
      : null;
  const healthEvent =
    openEvent?.type === 'health' && openEvent.idx >= 0
      ? device.data.healthEvents?.[openEvent.idx]
      : null;

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader deviceId={params.deviceId} />

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
              </TableRow>
            </TableHeader>
            <TableBody>
              {device.data.suspiciousEvents.map((event, idx) => (
                <TableRow
                  key={idx}
                  className="cursor-pointer hover:bg-accent/30"
                  onClick={() => setOpenEvent({ type: 'suspicious', idx })}
                >
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
                <TableRow
                  key={idx}
                  className="cursor-pointer hover:bg-accent/30"
                  onClick={() => setOpenEvent({ type: 'health', idx })}
                >
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

      {/* Modal Dialog for Event Details */}
      <Dialog open={!!openEvent} onOpenChange={(open) => !open && setOpenEvent(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {openEvent?.type === 'suspicious'
                ? 'Suspicious Event Details'
                : openEvent?.type === 'health'
                ? 'Health Event Details'
                : ''}
            </DialogTitle>
            <DialogDescription>
              {openEvent?.type === 'suspicious'
                ? 'Detailed information for this suspicious event.'
                : openEvent?.type === 'health'
                ? 'Detailed information for this health event.'
                : ''}
            </DialogDescription>
          </DialogHeader>
          {suspiciousEvent && (
            <div className="flex flex-col gap-2 mt-2">
              <div>
                <span className="font-semibold">Type:</span> {suspiciousEvent.type.replace(/_/g, ' ')}
              </div>
              <div>
                <span className="font-semibold">Confidence:</span> {(suspiciousEvent.confidence * 100).toFixed(1)}%
              </div>
              <div>
                <span className="font-semibold">Marked:</span> {suspiciousEvent.marked}
              </div>
              <div>
                <span className="font-semibold">Timestamp:</span> {new Date(suspiciousEvent.timestamp).toLocaleString('en-US', {
                  month: 'long',
                  day: 'numeric',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
              {suspiciousEvent.url && (
                <div>
                  <span className="font-semibold">Image:</span>
                  <div className="mt-1">
                    <Image src={suspiciousEvent.url} alt="event" width={300} height={200} className="rounded border object-cover" />
                  </div>
                </div>
              )}
            </div>
          )}
          {healthEvent && (
            <div className="flex flex-col gap-2 mt-2">
              <div>
                <span className="font-semibold">Type:</span> {healthEvent.type.replace(/_/g, ' ')}
              </div>
              <div>
                <span className="font-semibold">Severity:</span> {healthEvent.severity}
              </div>
              <div>
                <span className="font-semibold">Timestamp:</span> {new Date(healthEvent.timestamp).toLocaleString('en-US', {
                  month: 'long',
                  day: 'numeric',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>
          )}
          <DialogClose asChild>
            <Button onClick={() => setOpenEvent(null)} className="hover:bg-primary/90 mt-4">Close</Button>
          </DialogClose>
        </DialogContent>
      </Dialog>
    </section>
  );
}
