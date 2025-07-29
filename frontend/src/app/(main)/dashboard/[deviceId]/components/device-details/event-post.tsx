'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Eye, Loader2, ImageOff } from 'lucide-react';
import Image from 'next/image';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

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

interface EventPostProps {
  event: ProcessedEvent;
  token: string | null;
  onViewDetails: (event: ProcessedEvent) => void;
}

const EventPost: React.FC<EventPostProps> = ({
  event: initialEvent,
  token,
  onViewDetails,
}) => {
  const [event, setEvent] = useState<ProcessedEvent>(initialEvent);
  const [isLoading, setIsLoading] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  // Fetch images when the component mounts if they haven't been fetched
  useEffect(() => {
    const fetchEventImages = async () => {
      if (!token || event.imagesFetched || !event.image_c_key) return;
  
      // Abort previous requests
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
  
      setIsLoading(true);
      setEvent((prev) => ({ ...prev, fetchingImages: true }));
  
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
          }));
        } else {
          throw new Error(data?.error || 'Failed to fetch images');
        }
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          console.error(`Error fetching images for event ${event.id}:`, error);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
          setEvent((prev) => ({ ...prev, fetchingImages: false }));
        }
      }
    };

    fetchEventImages();

    // Cleanup function
    return () => {
      controllerRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event.id, event.imagesFetched, token]);


  const getSeverity = () => {
    switch (event.event_severity) {
      case '1':
        return {
          label: 'Low',
          className: 'border-yellow-500 bg-yellow-400 text-black',
        };
      case '2':
        return {
          label: 'High',
          className: 'border-orange-600 bg-orange-500 text-white',
        };
      case '3':
        return {
          label: 'Critical',
          className: 'border-red-700 bg-red-600 text-white',
        };
      default:
        return null;
    }
  };

  const severity = getSeverity();
  const hasImages = event.croppedImageUrl || event.fullImageUrl;

  console.log(event);

  return (
    <Card className="flex flex-col justify-between shadow-md hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex justify-between items-start">
            <CardTitle className="text-lg font-semibold">{event.eventstr}</CardTitle>
            {severity && (
                <Badge variant="outline" className={cn('ml-2', severity.className)}>
                {severity.label}
                </Badge>
            )}
        </div>
        <p className="text-xs text-gray-500">
          {new Date(event.timestamp).toLocaleString()}
        </p>
      </CardHeader>
      <CardContent className="flex-grow">
        <div className="relative w-full h-48 bg-gray-100 rounded-md flex items-center justify-center overflow-hidden">
          {isLoading && (
            <div className="flex flex-col items-center gap-2 text-gray-500">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span className="text-sm">Loading Image...</span>
            </div>
          )}
          {!isLoading && hasImages && (
            <Image
              src={event.fullImageUrl || event.croppedImageUrl!}
              alt={event.eventstr}
              fill
              className="object-cover"
            />
          )}
          {!isLoading && !hasImages && (
            <div className="flex flex-col items-center gap-2 text-gray-400">
              <ImageOff className="h-8 w-8" />
              <span className="text-sm">No Image</span>
            </div>
          )}
        </div>
      </CardContent>
      <CardFooter>
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={() => onViewDetails(event)}
        >
          <Eye className="h-4 w-4 mr-2" />
          View Details
        </Button>
      </CardFooter>
    </Card>
  );
};

export default EventPost;