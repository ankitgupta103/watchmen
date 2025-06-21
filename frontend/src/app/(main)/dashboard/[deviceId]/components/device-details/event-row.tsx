import React, { useEffect, useRef, useState } from 'react';
import { Eye, Loader2 } from 'lucide-react';
import Image from 'next/image';

import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { cn } from '@/lib/utils';

interface ProcessedEvent {
  id: string;
  machineId: number;
  timestamp: string | Date;
  eventstr: string;
  image_c_key: string;
  image_f_key: string;
  croppedImageUrl?: string;
  fullImageUrl?: string;
  imagesFetched: boolean;
  fetchingImages: boolean;
  event_severity?: string;
}

interface EventRowProps {
  event: ProcessedEvent;
  token: string | null;
  onViewDetails: (event: ProcessedEvent) => void;
}

const EventRow: React.FC<EventRowProps> = ({
  event: initialEvent,
  token,
  onViewDetails,
}) => {
  const [event, setEvent] = useState<ProcessedEvent>(initialEvent);
  const [isLoadingImages, setIsLoadingImages] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  const fetchEventImages = async () => {
    if (!token || event.imagesFetched || isLoadingImages) return;

    // Abort any previous request
    if (controllerRef.current) {
      controllerRef.current.abort();
    }

    const controller = new AbortController();
    controllerRef.current = controller;
    setIsLoadingImages(true);

    try {
      const data = await fetcherClient<{
        success: boolean;
        cropped_image_url?: string;
        full_image_url?: string;
        error?: string;
      }>(`${API_BASE_URL}/event-images/`, token, {
        method: 'POST',
        body: {
          image_c_key: event.image_c_key,
          image_f_key: event.image_f_key,
        },
        signal: controller.signal,
      });

      if (controller.signal.aborted) return;

      if (data?.success) {
        setEvent((prev) => ({
          ...prev,
          croppedImageUrl: data.cropped_image_url,
          fullImageUrl: data.full_image_url,
          imagesFetched: true,
          fetchingImages: false,
        }));
      } else {
        throw new Error(data?.error || 'Failed to fetch images');
      }
    } catch (error: unknown) {
      if (error instanceof Error && error.name !== 'AbortError') {
        console.error('Error fetching images for event:', event.id, error);
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoadingImages(false);
      }
    }
  };

  useEffect(() => {
    fetchEventImages();

    return () => {
      if (controllerRef.current) {
        controllerRef.current.abort();
      }
    };
  }, []);

  useEffect(() => {
    setEvent(initialEvent);
  }, [initialEvent]);

  const formatTimestamp = (timestamp: string | Date) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const handleViewDetails = () => {
    onViewDetails(event);
  };

  return (
    <tr className="border-b border-gray-200 hover:bg-gray-50">
      <td className="px-4 py-3">
        <div className="text-xs text-gray-900">
          {formatTimestamp(event.timestamp)}
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="space-y-1">
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500">EventStr: </span>
            <Badge variant="outline">
              {(event?.croppedImageUrl || event?.fullImageUrl)
                ?.split('/')
                .pop()
                ?.split('_')[0] || 'N/A'}
            </Badge>{' '}
          </div>
          <Separator />
          <div className="flex items-center gap-1">
            {event?.event_severity && (
              <>
                <span className="text-xs text-gray-500">Severity: </span>
                <Badge
                  variant="outline"
                  className={cn(
                    event?.event_severity === '1' &&
                      'border-yellow-500 bg-yellow-400 text-black',
                    event?.event_severity === '2' &&
                      'border-orange-600 bg-orange-500 text-white',
                    event?.event_severity === '3' &&
                      'border-red-700 bg-red-600 text-white',
                  )}
                >
                  {event?.event_severity === '1'
                    ? 'Low'
                    : event?.event_severity === '2'
                      ? 'High'
                      : 'Critical'}
                </Badge>
              </>
            )}
          </div>
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center space-x-2">
          {isLoadingImages ? (
            <div className="flex items-center space-x-2">
              <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
              <span className="text-xs text-gray-500">Loading images...</span>
            </div>
          ) : event.imagesFetched && event.croppedImageUrl ? (
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
            <span className="text-xs text-gray-400">No image</span>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        <button
          onClick={handleViewDetails}
          className="inline-flex items-center space-x-1 rounded-md border border-gray-300 bg-white px-3 py-1 text-sm hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:outline-none"
        >
          <Eye className="h-3 w-3" />
          <span>View</span>
        </button>
      </td>
    </tr>
  );
};

export default EventRow;
