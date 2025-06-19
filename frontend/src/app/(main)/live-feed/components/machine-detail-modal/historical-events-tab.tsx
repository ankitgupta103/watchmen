'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Clock, ImageIcon, Loader2 } from 'lucide-react';
import Image from 'next/image';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { cn } from '@/lib/utils';

import Pagination from './pagination';

interface MachineEvent {
  id: string;
  timestamp: Date;
  eventstr: string;
  image_c_key?: string;
  image_f_key?: string;
  cropped_image_url?: string;
  full_image_url?: string;
  images_loaded: boolean;
  images_requested: boolean;
  event_severity?: string;
}

const fetchEventImages = async (
  token: string,
  imageKeys: { image_c_key: string; image_f_key: string },
) => {
  try {
    const data = await fetcherClient<{
      success: boolean;
      cropped_image_url?: string;
      full_image_url?: string;
      error?: string;
    }>(`${API_BASE_URL}/event-images/`, token, {
      method: 'POST',
      body: imageKeys,
    });
    if (data?.success) {
      return {
        croppedImageUrl: data.cropped_image_url,
        fullImageUrl: data.full_image_url,
      };
    }
    throw new Error(data?.error || 'Failed to fetch images');
  } catch (error) {
    console.error('Error fetching images:', error);
    return null;
  }
};

const HistoricalEventsTab = ({
  machineId,
  token,
  orgId,
  onImageClick,
}: {
  machineId: number;
  token: string | null;
  orgId: number | null;
  onImageClick: (url: string) => void;
}) => {
  const [events, setEvents] = useState<MachineEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const eventsPerPage = 15;

  const fetchHistoricalEvents = useCallback(async () => {
    if (!token || !orgId) return;
    setLoading(true);
    setEvents([]);
    setCurrentPage(1);

    const promises = Array.from({ length: 7 }).map((_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateStr = date.toLocaleDateString('en-CA'); //  आएन-CA
      return fetcherClient<{
        success: boolean;
        events?: Array<{
          image_c_key: string;
          image_f_key: string;
          eventstr: string;
          timestamp?: string | Date;
        }>;
      }>(`${API_BASE_URL}/s3-events/fetch-events/`, token, {
        method: 'POST',
        body: { org_id: orgId, date: dateStr, machine_id: machineId },
      }).then((result) => (result?.success ? result?.events || [] : []));
    });

    const results = await Promise.all(promises);
    const allEvents = results.flat().map((event, index) => ({
      ...event,
      id: `hist-${machineId}-${index}`,
      timestamp: new Date(event.timestamp || Date.now()),
      images_loaded: false,
      images_requested: false,
    }));

    allEvents.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
    setEvents(allEvents);
    setLoading(false);
  }, [machineId, token, orgId]);

  useEffect(() => {
    fetchHistoricalEvents();
  }, [fetchHistoricalEvents]);

  // Fetch images for the current page
  useEffect(() => {
    if (events.length === 0 || !token) return;

    const startIndex = (currentPage - 1) * eventsPerPage;
    const endIndex = startIndex + eventsPerPage;
    const currentEvents = events.slice(startIndex, endIndex);

    currentEvents.forEach((event) => {
      if (event.image_c_key && event.image_f_key && !event.images_requested) {
        setEvents((prev) =>
          prev.map((e) =>
            e.id === event.id ? { ...e, images_requested: true } : e,
          ),
        );

        fetchEventImages(token, {
          image_c_key: event.image_c_key,
          image_f_key: event.image_f_key,
        }).then((imageUrls) => {
          setEvents((prev) =>
            prev.map((e) =>
              e.id === event.id
                ? {
                    ...e,
                    cropped_image_url: imageUrls?.croppedImageUrl,
                    full_image_url: imageUrls?.fullImageUrl,
                    images_loaded: true,
                  }
                : e,
            ),
          );
        });
      }
    });
  }, [events, currentPage, token]);

  const groupedEvents = useMemo(() => {
    return events.reduce(
      (acc, event) => {
        const dateKey = event.timestamp.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          weekday: 'long',
        });
        if (!acc[dateKey]) {
          acc[dateKey] = [];
        }
        acc[dateKey].push(event);
        return acc;
      },
      {} as Record<string, MachineEvent[]>,
    );
  }, [events]);

  const paginatedKeys = useMemo(() => {
    const allEventsFlat = Object.values(groupedEvents).flat();
    const totalPages = Math.ceil(allEventsFlat.length / eventsPerPage);
    const startIndex = (currentPage - 1) * eventsPerPage;
    const paginated = allEventsFlat.slice(
      startIndex,
      startIndex + eventsPerPage,
    );
    return {
      events: paginated,
      totalPages: totalPages,
    };
  }, [groupedEvents, currentPage]);

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-10 w-10 animate-spin text-gray-400" />
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="py-12 text-center">
        <ImageIcon className="mx-auto mb-4 h-16 w-16 text-gray-300" />
        <h3 className="mb-2 text-lg font-medium text-gray-600">
          No Historical Events
        </h3>
        <p className="text-sm text-gray-500">
          No events found for this machine in the past 7 days.
        </p>
      </div>
    );
  }

  const ImageDisplay = ({ event }: { event: MachineEvent }) => {
    const hasImageKeys = event.image_c_key && event.image_f_key;

    if (event.images_requested && !event.images_loaded) {
      return (
        <div className="flex h-32 items-center justify-center rounded border bg-gray-50">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      );
    }

    if (
      event.images_loaded &&
      (event.cropped_image_url || event.full_image_url)
    ) {
      return (
        <div className="grid grid-cols-2 gap-2">
          {event.cropped_image_url && (
            <Image
              src={event.cropped_image_url}
              alt="Cropped historical"
              width={150}
              height={150}
              className="h-24 w-full cursor-pointer rounded border object-cover"
              onClick={() => onImageClick(event.cropped_image_url!)}
            />
          )}
          {event.full_image_url && (
            <Image
              src={event.full_image_url}
              alt="Full historical"
              width={150}
              height={150}
              className="h-24 w-full cursor-pointer rounded border object-cover"
              onClick={() => onImageClick(event.full_image_url!)}
            />
          )}
        </div>
      );
    }

    if (hasImageKeys) {
      return (
        <div className="flex h-32 flex-col items-center justify-center rounded border bg-blue-50/50 text-center text-xs text-blue-600">
          <ImageIcon className="mb-1 h-6 w-6" />
          Images Available
        </div>
      );
    }

    return (
      <div className="flex h-32 flex-col items-center justify-center rounded border bg-gray-50 text-center text-xs text-gray-500">
        <ImageIcon className="mb-1 h-6 w-6 text-gray-400" />
        No Image Data
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <div className="space-y-6">
        {Object.entries(
          paginatedKeys.events.reduce(
            (acc, event) => {
              const dateKey = event.timestamp.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                weekday: 'long',
              });
              if (!acc[dateKey]) {
                acc[dateKey] = [];
              }
              acc[dateKey].push(event);
              return acc;
            },
            {} as Record<string, MachineEvent[]>,
          ),
        ).map(([date, dateEvents]) => (
          <div key={date}>
            <div className="mb-3 border-b pb-2">
              <h4 className="font-semibold text-gray-800">{date}</h4>
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {dateEvents.map((event) => (
                <Card key={event.id}>
                  <CardContent className="space-y-3 p-3">
                    <div className="flex items-start justify-between text-sm">
                      <Badge
                        variant="outline"
                        className={cn(
                          event?.event_severity === '1' &&
                            'bg-yellow-500 text-white',
                          event?.event_severity === '2' &&
                            'bg-orange-500 text-white',
                          event?.event_severity === '3' &&
                            'bg-red-500 text-white',
                        )}
                      >
                        {event?.event_severity === '1'
                          ? 'Low'
                          : event?.event_severity === '2'
                            ? 'High'
                            : 'Critical'}
                      </Badge>
                      <span className="text-gray-500">
                        {event.timestamp.toLocaleDateString()}
                      </span>
                    </div>
                    <ImageDisplay event={event} />
                    <div className="flex items-center justify-end gap-2 text-xs text-gray-500">
                      <Clock className="h-3 w-3" />
                      {event.timestamp.toLocaleTimeString()}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>
      {paginatedKeys.totalPages > 1 && (
        <Pagination
          currentPage={currentPage}
          totalPages={paginatedKeys.totalPages}
          onPageChange={setCurrentPage}
        />
      )}
    </div>
  );
};

export default HistoricalEventsTab;
