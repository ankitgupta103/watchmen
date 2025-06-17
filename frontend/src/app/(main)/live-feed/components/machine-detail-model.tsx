import React, { useState } from 'react';
import { Calendar, Camera, Clock, Loader2, MapPin, X } from 'lucide-react';
import Image from 'next/image';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';

import { Machine } from '@/lib/types/machine';
import { formatBufferSize, toTitleCase } from '@/lib/utils';

interface MachineEvent {
  id: string;
  timestamp: Date;
  eventstr: string;
  image_c_key?: string;
  image_f_key?: string;
  cropped_image_url?: string;
  full_image_url?: string;
  images_loaded?: boolean;
}

interface SimpleMachineData {
  machine_id: number;
  events: MachineEvent[];
  event_count: number;
  last_event?: MachineEvent;
  last_updated: string;
  // Status and location from useMachineStats
  is_online: boolean;
  location: { lat: number; lng: number };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  stats_data: any;
  buffer_size: number;
}

interface MachineDetailModalProps {
  selectedMachine: Machine | null;
  setSelectedMachine: React.Dispatch<React.SetStateAction<Machine | null>>;
  getMachineData: (machineId: number) => SimpleMachineData;
}

export default function MachineDetailModal({
  selectedMachine,
  setSelectedMachine,
  getMachineData,
}: MachineDetailModalProps) {
  const [selectedImageUrl, setSelectedImageUrl] = useState<string | null>(null);

  if (!selectedMachine) return null;

  const machineData = getMachineData(selectedMachine.id);

  // Format time elapsed
  const getTimeElapsed = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);

    if (minutes > 0) {
      return `${minutes}m ${seconds}s ago`;
    }
    return `${seconds}s ago`;
  };

  return (
    <>
      <Dialog
        open={!!selectedMachine}
        onOpenChange={() => setSelectedMachine(null)}
      >
        <DialogContent className="flex h-full max-h-[90vh] w-full max-w-4xl flex-col overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-xl">
              <Camera className="h-6 w-6 text-blue-600" />
              {toTitleCase(selectedMachine.name)}

              {machineData.event_count > 0 && (
                <Badge
                  variant="outline"
                  className="border-orange-300 text-orange-700"
                >
                  {machineData.event_count} Event
                  {machineData.event_count > 1 ? 's' : ''}
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-6">
            {/* Machine Info Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <MapPin className="h-5 w-5" />
                  Machine Information
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Machine ID:
                  </span>
                  <div className="text-sm">{selectedMachine.id}</div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Machine UID:
                  </span>
                  <div className="text-sm">{selectedMachine.machine_uid}</div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Type:
                  </span>
                  <div className="text-sm capitalize">
                    {selectedMachine.type.replace('_', ' ')}
                  </div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Status:
                  </span>
                  <div className="text-sm">
                    <Badge
                      variant={
                        machineData.is_online ? 'default' : 'destructive'
                      }
                    >
                      {machineData.is_online ? 'Online' : 'Offline'}
                    </Badge>
                  </div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Location:
                  </span>
                  <div className="text-sm">
                    {machineData.location.lat.toFixed(6)},{' '}
                    {machineData.location.lng.toFixed(6)}
                  </div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Owner:
                  </span>
                  <div className="text-sm">
                    {selectedMachine.current_owner_name}
                  </div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Buffer Size:
                  </span>
                  <div className="text-sm">
                    {formatBufferSize(machineData.buffer_size)}
                  </div>
                </div>
                {machineData.last_event && (
                  <div className="col-span-full">
                    <span className="text-sm font-medium text-gray-500">
                      Last Event:
                    </span>
                    <div className="text-sm">
                      {machineData.last_event.eventstr} -{' '}
                      {getTimeElapsed(machineData.last_event.timestamp)}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Separator />

            {/* Events Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold">Recent Events</h3>
                {machineData.event_count > 0 && (
                  <Badge variant="outline">
                    {machineData.event_count} event
                    {machineData.event_count > 1 ? 's' : ''}
                  </Badge>
                )}
              </div>

              {machineData.events.length === 0 ? (
                <div className="py-12 text-center">
                  <Camera className="mx-auto mb-4 h-16 w-16 text-gray-300" />
                  <h3 className="mb-2 text-lg font-medium text-gray-600">
                    No Events Detected
                  </h3>
                  <p className="text-gray-500">
                    This machine hasn&apos;t triggered any events yet
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {machineData.events
                    .sort(
                      (a, b) =>
                        new Date(b.timestamp).getTime() -
                        new Date(a.timestamp).getTime(),
                    )
                    .map((event) => (
                      <Card
                        key={event.id}
                        className="border-l-4 border-l-orange-500 bg-orange-50/30"
                      >
                        <CardContent className="space-y-3 p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              <Badge variant="secondary">Event</Badge>
                              <div className="text-sm">
                                <span className="font-medium">
                                  {event.eventstr}
                                </span>
                              </div>
                            </div>
                            <div className="flex items-center gap-1">
                              <Clock className="h-3 w-3 text-gray-400" />
                              <span className="text-xs text-gray-500">
                                {getTimeElapsed(event.timestamp)}
                              </span>
                            </div>
                          </div>

                          {/* Image Display */}
                          {event.images_loaded &&
                          (event.cropped_image_url || event.full_image_url) ? (
                            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                              {event.cropped_image_url && (
                                <div className="space-y-2">
                                  <div className="text-sm font-medium text-gray-700">
                                    Cropped Image:
                                  </div>
                                  <Image
                                    src={event.cropped_image_url}
                                    alt={`Cropped image for event ${event.eventstr}`}
                                    width={200}
                                    height={150}
                                    className="cursor-pointer rounded-lg border shadow-sm transition-transform hover:scale-105"
                                    onClick={() =>
                                      setSelectedImageUrl(
                                        event.cropped_image_url!,
                                      )
                                    }
                                  />
                                </div>
                              )}
                              {event.full_image_url && (
                                <div className="space-y-2">
                                  <div className="text-sm font-medium text-gray-700">
                                    Full Image:
                                  </div>
                                  <Image
                                    src={event.full_image_url}
                                    alt={`Full image for event ${event.eventstr}`}
                                    width={200}
                                    height={150}
                                    className="cursor-pointer rounded-lg border shadow-sm transition-transform hover:scale-105"
                                    onClick={() =>
                                      setSelectedImageUrl(event.full_image_url!)
                                    }
                                  />
                                </div>
                              )}
                            </div>
                          ) : !event.images_loaded &&
                            (event.image_c_key || event.image_f_key) ? (
                            <div className="flex items-center gap-2 text-sm text-gray-500">
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Loading images...
                            </div>
                          ) : (
                            <div className="text-sm text-gray-500">
                              No images available for this event
                            </div>
                          )}

                          <div className="text-xs text-gray-500">
                            <Calendar className="mr-1 inline h-3 w-3" />
                            {new Date(event.timestamp).toLocaleString()}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Image Viewer Modal */}
      {selectedImageUrl && (
        <Dialog
          open={!!selectedImageUrl}
          onOpenChange={() => setSelectedImageUrl(null)}
        >
          <DialogContent className="max-h-[90vh] max-w-4xl p-2">
            <DialogHeader className="pb-2">
              <DialogTitle className="flex items-center justify-between">
                Event Image
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedImageUrl(null)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </DialogTitle>
            </DialogHeader>
            <div className="flex items-center justify-center">
              <Image
                src={selectedImageUrl}
                alt="Event image full view"
                width={800}
                height={600}
                className="max-h-[70vh] w-auto rounded-lg"
              />
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
