'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
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

import EventRow from './event-row';
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

  const eventsPerPage = 10;
  const controllerRef = useRef<AbortController | null>(null);

  const fetchEventsForDateRange = useCallback(
    async (days: number) => {
      if (!token) return;

      // Abort previous request
      if (controllerRef.current) {
        controllerRef.current.abort();
      }

      const controller = new AbortController();
      controllerRef.current = controller;

      setLoading(true);
      setEvents([]);

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
          signal: controller.signal,
        });

        if (controller.signal.aborted) return;

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

        if (!controller.signal.aborted) {
          setEvents(sortedEvents);
          setCurrentPage(1);
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== 'AbortError') {
          console.error('Error fetching events:', err);
          if (!controller.signal.aborted) {
            setEvents([]);
          }
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    },
    [token, orgId, device.id],
  );

  // Effect for fetching events when date range changes
  useEffect(() => {
    fetchEventsForDateRange(parseInt(dateRange));

    return () => {
      if (controllerRef.current) {
        controllerRef.current.abort();
      }
    };
  }, [dateRange, fetchEventsForDateRange]);

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
                <span>Loading events...</span>
              </div>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading && events.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin" />
            <span className="ml-2 text-gray-600">Loading events...</span>
          </div>
        ) : events.length > 0 ? (
          <div>
            <div className="mb-4 text-sm text-gray-600">
              Found {events.length} events in the last {dateRange} days.
            </div>

            {/* Events Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50">
                    <th className="px-4 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
                      Timestamp
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
                      Event Description
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
                      Images
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {currentEvents.map((event) => (
                    <EventRow
                      key={event.id}
                      event={event}
                      token={token}
                      onViewDetails={onEventSelect}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="mt-4">
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={setCurrentPage}
                />
              </div>
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
