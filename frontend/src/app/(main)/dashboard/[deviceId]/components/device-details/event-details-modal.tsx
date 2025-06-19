'use client';

import React, { useEffect } from 'react';
import { Info, Loader2, X } from 'lucide-react';
import Image from 'next/image';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import { Machine } from '@/lib/types/machine';

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

const EventDetailsModal = ({
  event,
  device,
  onClose,
  onFetchImages,
}: {
  event: ProcessedEvent;
  device: Machine;
  onClose: () => void;
  onFetchImages: (event: ProcessedEvent) => Promise<ProcessedEvent | void>;
}) => {
  useEffect(() => {
    if (!event.imagesFetched && !event.fetchingImages) {
      onFetchImages(event);
    }
  }, [event, onFetchImages]);

  return (
    <div className="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="max-h-[90vh] w-full max-w-4xl overflow-auto">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Info className="h-6 w-6" />
              Event Details
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-semibold text-gray-600">Event:</span>
                <p>{event.eventstr}</p>
              </div>
              <div>
                <span className="font-semibold text-gray-600">Timestamp:</span>
                <p>{new Date(event.timestamp).toLocaleString()}</p>
              </div>
              <div>
                <span className="font-semibold text-gray-600">Machine:</span>
                <p>{device.name}</p>
              </div>
              <div>
                <span className="font-semibold text-gray-600">Machine ID:</span>
                <p>{event.machineId}</p>
              </div>
            </div>

            {event.fetchingImages && (
              <div className="flex items-center justify-center py-8">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <span>Loading images...</span>
                </div>
              </div>
            )}

            {event.imagesFetched && (
              <div className="space-y-4">
                <h3 className="font-semibold">Event Images</h3>
                <div className="flex flex-col items-center justify-center gap-4 lg:flex-row">
                  {event.croppedImageUrl && (
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-gray-600">
                        Cropped Image
                      </p>
                      <div className="relative w-full overflow-hidden rounded border">
                        <Image
                          src={event.croppedImageUrl}
                          alt="Cropped event image"
                          width={400}
                          height={600} // Example aspect ratio
                          className="h-80 w-fit object-contain"
                        />
                      </div>
                    </div>
                  )}
                  {event.fullImageUrl && (
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-gray-600">
                        Full Image
                      </p>
                      <div className="relative w-full overflow-hidden rounded border">
                        <Image
                          src={event.fullImageUrl}
                          alt="Full event image"
                          width={600} // Example aspect ratio
                          height={400}
                          className="h-80 w-fit object-contain"
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default EventDetailsModal;
