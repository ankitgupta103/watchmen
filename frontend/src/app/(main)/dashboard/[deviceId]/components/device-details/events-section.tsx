'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { Activity, Loader2 } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { Machine } from '@/lib/types/machine';

import EventsTable from './events-table';
import Pagination from './pagination';

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

const EventsSection = ({
  device,
  orgId,
  token,
  onEventSelect,
}: {
  device: Machine;
  orgId: number;
  token: string | null;
  onEventSelect: (event: ProcessedEvent) => void;
}) => {
  const [events, setEvents] = useState<ProcessedEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<'7' | '30' | '90'>('30');

  const [currentPage, setCurrentPage] = useState(1);
  const eventsPerPage = 15;

  const fetchEventImages = async (
    token: string | null,
    imageKeys: { image_c_key: string; image_f_key: string },
  ) => {
    if (!token) {
      console.error('No authentication token available');
      return null;
    }
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
      } else {
        throw new Error(data?.error || 'Failed to fetch images');
      }
    } catch (error) {
      console.error('Error fetching images:', error);
      return null;
    }
  };

  const fetchEventsForDateRange = useCallback(
    async (days: number) => {
      if (!token) return;
      setLoading(true);

      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);
      const startDateStr = startDate.toISOString().split('T')[0];
      const endDateStr = endDate.toISOString().split('T')[0];

      try {
        const result = await fetcherClient<{
          success: boolean;
          date_events?: { [date: string]: S3EventData[] };
          error?: string;
        }>(`${API_BASE_URL}/s3-events/fetch-events/`, token, {
          method: 'PUT',
          body: {
            org_id: orgId,
            start_date: startDateStr,
            end_date: endDateStr,
            machine_ids: [device.id],
          },
        });

        if (!result?.success) {
          throw new Error(result?.error || 'Failed to fetch events');
        }

        const dateEvents = result.date_events || {};
        const allEvents: ProcessedEvent[] = [];
        Object.entries(dateEvents).forEach(([dateStr, dayEvents]) => {
          const processedEvents: ProcessedEvent[] = (
            dayEvents as S3EventData[]
          ).map((s3Event, index) => ({
            ...s3Event,
            id: `${device.id}-${dateStr}-${index}`,
            machineId: device.id,
            timestamp: s3Event.timestamp
              ? new Date(s3Event.timestamp)
              : new Date(dateStr + 'T12:00:00'),
            imagesFetched: false,
            fetchingImages: false,
          }));
          allEvents.push(...processedEvents);
        });

        const sortedEvents = allEvents.sort(
          (a, b) =>
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
        );

        setEvents(sortedEvents);
        setCurrentPage(1); // Reset to first page
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (err: any) {
        console.error('Error fetching events:', err);
      } finally {
        setLoading(false);
      }
    },
    [token, orgId, device.id],
  );

  const fetchImagesForCurrentPage = useCallback(
    async (page: number) => {
      const startIndex = (page - 1) * eventsPerPage;
      const endIndex = startIndex + eventsPerPage;
      const eventsForPage = events.slice(startIndex, endIndex);

      const eventsToFetch = eventsForPage.filter(
        (event) => !event.imagesFetched && !event.fetchingImages,
      );

      if (eventsToFetch.length === 0) return;

      setEvents((prev) =>
        prev.map((e) =>
          eventsToFetch.some((etf) => etf.id === e.id)
            ? { ...e, fetchingImages: true }
            : e,
        ),
      );

      const updatedEvents = await Promise.all(
        eventsToFetch.map(async (event) => {
          const imageUrls = await fetchEventImages(token, {
            image_c_key: event.image_c_key,
            image_f_key: event.image_f_key,
          });
          return {
            ...event,
            croppedImageUrl: imageUrls?.croppedImageUrl,
            fullImageUrl: imageUrls?.fullImageUrl,
            imagesFetched: true,
            fetchingImages: false,
          };
        }),
      );

      setEvents((prev) => {
        const updatedState = [...prev];
        updatedEvents.forEach((updatedEvent) => {
          const index = updatedState.findIndex((e) => e.id === updatedEvent.id);
          if (index !== -1) {
            updatedState[index] = updatedEvent;
          }
        });
        return updatedState;
      });
    },
    [events, token],
  );

  useEffect(() => {
    fetchEventsForDateRange(parseInt(dateRange));
  }, [dateRange, fetchEventsForDateRange]);

  useEffect(() => {
    if (events.length > 0) {
      fetchImagesForCurrentPage(currentPage);
    }
  }, [currentPage, events, fetchImagesForCurrentPage]);

  const totalPages = Math.ceil(events.length / eventsPerPage);
  const startIndex = (currentPage - 1) * eventsPerPage;
  const currentEvents = events.slice(startIndex, startIndex + eventsPerPage);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-6 w-6" />
            Recent Events
          </CardTitle>
          <div className="flex items-center gap-2">
            <Select
              value={dateRange}
              onValueChange={(value: '7' | '30' | '90') => setDateRange(value)}
              disabled={loading}
            >
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
            {loading && (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Loading...</span>
              </div>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : events.length > 0 ? (
          <div>
            <div className="mb-4 text-sm text-gray-600">
              Found {events.length} events in the last {dateRange} days.
            </div>
            <EventsTable events={currentEvents} onViewDetails={onEventSelect} />
            {totalPages > 1 && (
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
              />
            )}
          </div>
        ) : (
          <div className="py-12 text-center text-gray-500">
            <Activity className="mx-auto mb-4 h-16 w-16 opacity-30" />
            <p className="text-lg font-medium">No events found</p>
            <p className="text-sm">
              No events recorded for this device in the last {dateRange} days.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default EventsSection;
