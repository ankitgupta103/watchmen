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

import EventPost from './event-post';
import Pagination from './pagination';

interface S3EventData {
  image_c_key: string;
  image_f_key: string;
  eventstr: string;
  timestamp?: string | Date;
  machineId?: number;
  event_severity?: string;
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
  // BUG FIX: Changed 'all ' to 'all' to match the SelectItem value
  const [dateRange, setDateRange] = useState<'7' | '30' | '90' | '180' | '365' | 'all'>('30');
  const [currentPage, setCurrentPage] = useState(1);

  const eventsPerPage = 9; // Changed for better grid layout
  const controllerRef = useRef<AbortController | null>(null);

  const fetchEventsForDateRange = useCallback(
    async (days: number | null) => {
      if (!token) return;

      if (controllerRef.current) {
        controllerRef.current.abort();
      }

      const controller = new AbortController();
      controllerRef.current = controller;

      setLoading(true);
      setEvents([]);
      setCurrentPage(1);

      const endDate = new Date();
      let startDate: Date;
      
      if (days === null) {
        startDate = new Date('2020-01-01'); // All time
      } else {
        startDate = new Date();
        startDate.setDate(startDate.getDate() - days);
      }
      
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
            event_severity: s3Event.event_severity,
            eventstr: s3Event.eventstr,
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

  useEffect(() => {
    // BUG FIX: Correctly parse dateRange, treating 'all' as null for days
    const days = dateRange === 'all' ? null : parseInt(dateRange, 10);
    fetchEventsForDateRange(days);

    return () => {
      if (controllerRef.current) {
        controllerRef.current.abort();
      }
    };
  }, [dateRange, fetchEventsForDateRange]);

  const totalPages = Math.ceil(events.length / eventsPerPage);
  const startIndex = (currentPage - 1) * eventsPerPage;
  const currentEvents = events.slice(startIndex, startIndex + eventsPerPage);

  const getDynamicMessage = () => {
    if (dateRange === 'all') {
      return 'of all time';
    }
    return `in the last ${dateRange} days`;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="flex items-center gap-2 mb-4 sm:mb-0">
            <Activity className="h-6 w-6" />
            Recent Events
          </CardTitle>
          <div className="flex items-center gap-2">
            <Select
              value={dateRange}
              onValueChange={(value: '7' | '30' | '90' | '180' | '365' | 'all') =>
                setDateRange(value)
              }
              disabled={loading}
            >
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
                <SelectItem value="180">Last 180 days</SelectItem>
                <SelectItem value="365">Last 365 days</SelectItem>
                <SelectItem value="all">All time</SelectItem>
              </SelectContent>
            </Select>
            {loading && (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading && events.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin" />
            <span className="ml-2 text-gray-600">Loading events...</span>
          </div>
        ) : events.length > 0 ? (
          <div>
            <div className="mb-6 text-sm text-gray-600">
              Found {events.length} events {getDynamicMessage()}.
            </div>

            {/* NEW: Grid layout for event posts */}
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {currentEvents.map((event) => (
                <EventPost
                  key={event.id}
                  event={event}
                  token={token}
                  onViewDetails={onEventSelect}
                />
              ))}
            </div>

            {totalPages > 1 && (
              <div className="mt-8">
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={setCurrentPage}
                />
              </div>
            )}
          </div>
        ) : (
          <div className="py-16 text-center text-gray-500">
            <Activity className="mx-auto mb-4 h-16 w-16 opacity-30" />
            <p className="text-lg font-medium">No events found</p>
            <p className="text-sm">
              No events were recorded for this device {getDynamicMessage()}.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default EventsSection;