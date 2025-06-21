'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Clock, ImageIcon, Loader2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { cn } from '@/lib/utils';

import EventImage from './event-image';
import Pagination from './pagination';

interface MachineEvent {
  id: string;
  timestamp: Date;
  eventstr: string;
  image_c_key?: string;
  image_f_key?: string;
  event_severity?: string;
}

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
      const dateStr = date.toLocaleDateString('en-CA');
      return fetcherClient<{
        success: boolean;
        events?: Array<{
          image_c_key: string;
          image_f_key: string;
          eventstr: string;
          timestamp?: string | Date;
          event_severity?: string;
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
    }));

    allEvents.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
    setEvents(allEvents);
    setLoading(false);
  }, [machineId, token, orgId]);

  useEffect(() => {
    fetchHistoricalEvents();
  }, [fetchHistoricalEvents]);

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
  }, [groupedEvents, currentPage, eventsPerPage]);

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
                    <EventImage
                      token={token}
                      image_c_key={event.image_c_key}
                      image_f_key={event.image_f_key}
                      onImageClick={onImageClick}
                    />
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">
                        {(event?.image_c_key || event?.image_f_key)
                          ?.split('/')
                          .pop()
                          ?.split('_')[0] || 'N/A'}
                      </span>
                      <div className="flex items-center justify-end gap-2 text-xs text-gray-500">
                        <Clock className="h-3 w-3" />
                        {event.timestamp.toLocaleTimeString()}
                      </div>
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
