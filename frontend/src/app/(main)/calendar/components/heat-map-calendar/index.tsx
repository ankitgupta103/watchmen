'use client';

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  Activity,
  Camera,
  ChevronLeft,
  ChevronRight,
  Filter,
  Loader2,
} from 'lucide-react';
import Image from 'next/image';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import 'leaflet/dist/leaflet.css';

import useToken from '@/hooks/use-token';
import dynamic from 'next/dynamic';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { Machine } from '@/lib/types/machine';
import { cn } from '@/lib/utils';

import ImageViewerModal from './image-viewer';
import Pagination from './pagination';

const MapFilter = dynamic(() => import('../map-filter'), {
  ssr: false,
});

interface HeatMapCalendarProps {
  machines: Machine[];
  orgId: number;
}

interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

interface S3EventData {
  image_c_key: string;
  image_f_key: string;
  eventstr: string;
  timestamp?: string | Date;
  machineId?: number;
  event_severity?: string; // Ensure this is part of the API response
}

interface ProcessedEvent extends S3EventData {
  id: string;
  machineId: number;
  machineName: string;
  timestamp: string | Date;
  croppedImageUrl?: string;
  fullImageUrl?: string;
  imagesLoaded: boolean;
}

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export default function HeatMapCalendar({
  machines,
  orgId,
}: HeatMapCalendarProps) {
  const { token } = useToken();
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [showMapFilter, setShowMapFilter] = useState(false);
  const [areaFilter, setAreaFilter] = useState<MapBounds | null>(null);
  const [modalImage, setModalImage] = useState<{
    url: string;
    label: string;
  } | null>(null);

  // State for events, loading, and errors
  const [events, setEvents] = useState<Record<string, ProcessedEvent[]>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [loadingImages, setLoadingImages] = useState<Record<string, boolean>>(
    {},
  );

  // Refs to hold current state for use in callbacks without causing loops
  const eventsRef = useRef(events);
  eventsRef.current = events;
  const loadingRef = useRef(loading);
  loadingRef.current = loading;

  // Pagination state
  const [detailsCurrentPage, setDetailsCurrentPage] = useState(1);
  const eventsPerPage = 10;

  const filteredMachines = useMemo(() => {
    if (!areaFilter) return machines;
    return machines.filter(
      (machine) =>
        machine.last_location.lat >= areaFilter.south &&
        machine.last_location.lat <= areaFilter.north &&
        machine.last_location.long >= areaFilter.west &&
        machine.last_location.long <= areaFilter.east,
    );
  }, [machines, areaFilter]);

  const fetchEventsForDate = useCallback(
    async (date: Date) => {
      if (!token) return;
      const dateStr = date.toLocaleDateString('en-CA');
      if (loadingRef.current[dateStr] || eventsRef.current[dateStr]) return;

      setLoading((prev) => ({ ...prev, [dateStr]: true }));
      try {
        const machinesToCheck = areaFilter ? filteredMachines : machines;
        const allEvents: ProcessedEvent[] = [];
        for (const machine of machinesToCheck) {
          try {
            const result = await fetcherClient<{
              success: boolean;
              events?: S3EventData[];
            }>(`${API_BASE_URL}/s3-events/fetch-events/`, token, {
              method: 'POST',
              body: { org_id: orgId, date: dateStr, machine_id: machine.id },
            });
            if (result?.success && result.events) {
              allEvents.push(
                ...result.events.map((event, index) => ({
                  ...event,
                  id: `${machine.id}-${dateStr}-${index}`,
                  machineId: machine.id,
                  machineName: machine.name,
                  timestamp: event.timestamp
                    ? new Date(event.timestamp)
                    : new Date(dateStr + 'T12:00:00'),
                  imagesLoaded: false,
                })),
              );
            }
          } catch (err) {
            console.warn(
              `Fetch failed for machine ${machine.id} on ${dateStr} ${err}`,
            );
          }
        }
        setEvents((prev) => ({ ...prev, [dateStr]: allEvents }));
      } catch (err) {
        console.error(`Failed to fetch events for ${dateStr}`, err);
      } finally {
        setLoading((prev) => ({ ...prev, [dateStr]: false }));
      }
    },
    [token, orgId, areaFilter, filteredMachines, machines],
  );

  const fetchImagesForEvents = useCallback(
    async (dateStr: string, eventList: ProcessedEvent[]) => {
      const eventsToFetch = eventList.filter(
        (e) => e.image_c_key && !e.imagesLoaded,
      );
      if (!token || eventsToFetch.length === 0) return;

      setLoadingImages((prev) => ({ ...prev, [dateStr]: true }));
      try {
        const imagePromises = eventsToFetch.map(async (event) => {
          try {
            const imageResult = await fetcherClient<{
              success: boolean;
              cropped_image_url?: string;
              full_image_url?: string;
            }>(`${API_BASE_URL}/event-images/`, token, {
              method: 'POST',
              body: {
                image_c_key: event.image_c_key,
                image_f_key: event.image_f_key,
              },
            });
            if (imageResult?.success) {
              return {
                ...event,
                croppedImageUrl: imageResult.cropped_image_url,
                fullImageUrl: imageResult.full_image_url,
                imagesLoaded: true,
              };
            }
          } catch (err) {
            console.warn(`Image fetch failed for event: ${event.id} ${err}`);
          }
          return { ...event, imagesLoaded: true };
        });

        const updatedEventsWithImages = await Promise.all(imagePromises);

        setEvents((prev) => {
          const newDayEvents = [...(prev[dateStr] || [])];
          updatedEventsWithImages.forEach((updatedEvent) => {
            const index = newDayEvents.findIndex(
              (e) => e.id === updatedEvent.id,
            );
            if (index !== -1) newDayEvents[index] = updatedEvent;
          });
          return { ...prev, [dateStr]: newDayEvents };
        });
      } finally {
        setLoadingImages((prev) => ({ ...prev, [dateStr]: false }));
      }
    },
    [token],
  );

  const getCalendarDays = useCallback(() => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    const days = [];
    for (let i = 0; i < 42; i++) {
      days.push(new Date(startDate));
      startDate.setDate(startDate.getDate() + 1);
    }
    return days;
  }, [currentMonth]);

  useEffect(() => {
    setEvents({});
    setLoading({});
    setLoadingImages({});
  }, [areaFilter]);

  // OPTIMIZED: Fetch events in parallel batches of 5
  useEffect(() => {
    const fetchInBatches = async () => {
      if (!token) return;
      const daysInMonth = getCalendarDays().filter(
        (day) => day.getMonth() === currentMonth.getMonth(),
      );

      const BATCH_SIZE = 5;
      for (let i = 0; i < daysInMonth.length; i += BATCH_SIZE) {
        const batch = daysInMonth.slice(i, i + BATCH_SIZE);
        const promises = batch.map((day) => fetchEventsForDate(day));
        await Promise.all(promises);
      }
    };
    fetchInBatches();
  }, [currentMonth, fetchEventsForDate, token, getCalendarDays]);

  const selectedDateEvents = useMemo(
    () =>
      (events[selectedDate.toLocaleDateString('en-CA')] || []).sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      ),
    [events, selectedDate],
  );

  const paginatedDetailsEvents = useMemo(() => {
    const startIndex = (detailsCurrentPage - 1) * eventsPerPage;
    return selectedDateEvents.slice(startIndex, startIndex + eventsPerPage);
  }, [selectedDateEvents, detailsCurrentPage]);

  // OPTIMIZED: Fetch images only for the visible page in the details panel
  useEffect(() => {
    if (paginatedDetailsEvents.length > 0) {
      const dateStr = selectedDate.toLocaleDateString('en-CA');
      fetchImagesForEvents(dateStr, paginatedDetailsEvents);
    }
  }, [paginatedDetailsEvents, selectedDate, fetchImagesForEvents]);

  useEffect(() => {
    setDetailsCurrentPage(1);
  }, [selectedDate]);

  const totalDetailsPages = Math.ceil(
    selectedDateEvents.length / eventsPerPage,
  );

  const navigateMonth = (direction: 'prev' | 'next') => {
    setCurrentMonth((prev) => {
      const newDate = new Date(prev);
      newDate.setMonth(prev.getMonth() + (direction === 'next' ? 1 : -1));
      return newDate;
    });
  };

  const isCurrentMonth = (date: Date) =>
    date.getMonth() === currentMonth.getMonth();
  const isToday = (date: Date) =>
    date.toDateString() === new Date().toDateString();
  const isSelected = (date: Date) =>
    date.toDateString() === selectedDate.toDateString();

  const getDateIntensity = (date: Date) => {
    const count = (events[date.toLocaleDateString('en-CA')] || []).length;
    if (count > 10) return 'critical';
    if (count > 5) return 'high';
    if (count > 2) return 'medium';
    if (count > 0) return 'low';
    return 'none';
  };

  const isLoadingAny = Object.values(loading).some(Boolean);

  return (
    <>
      {modalImage && (
        <ImageViewerModal
          modalImage={modalImage}
          setModalImage={setModalImage}
        />
      )}
      <div className="relative flex flex-col gap-4 overflow-y-auto xl:flex-row">
        <div className="mb-4 flex-1">
          <Card className="h-fit">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <CardTitle className="text-2xl font-bold">
                    {MONTHS[currentMonth.getMonth()]}{' '}
                    {currentMonth.getFullYear()}
                  </CardTitle>
                  <Button
                    variant={areaFilter ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setShowMapFilter(true)}
                  >
                    <Filter className="h-4 w-4" />
                    <span className="ml-2">
                      {areaFilter
                        ? `Filtered (${filteredMachines.length} machines)`
                        : 'Map Filter'}
                    </span>
                  </Button>
                  {isLoadingAny && (
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading...
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigateMonth('prev')}
                    disabled={isLoadingAny}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigateMonth('next')}
                    disabled={isLoadingAny}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-4 grid grid-cols-7 gap-2">
                {WEEKDAYS.map((day) => (
                  <div
                    key={day}
                    className="py-2 text-center text-sm font-medium text-gray-500"
                  >
                    {day}
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-7 gap-2">
                {getCalendarDays().map((date, index) => {
                  const dateStr = date.toLocaleDateString('en-CA');
                  const dayEventsCount = (events[dateStr] || []).length;
                  const dayEventsSeverity = (events[dateStr] || []).reduce(
                    (acc, event) => {
                      if (event?.event_severity) {
                        acc[event.event_severity] =
                          (acc[event.event_severity] || 0) + 1;
                      } else {
                        acc['0'] = (acc['0'] || 0) + 1;
                      }
                      return acc;
                    },
                    {
                      '0': 0,
                      '1': 0,
                      '2': 0,
                      '3': 0,
                    } as Record<string, number>,
                  );

                  return (
                    <Button
                      key={index}
                      onClick={() => setSelectedDate(date)}
                      className={cn(
                        'text-primary relative flex h-24 w-full flex-col items-start justify-start rounded-lg border-2 p-1 text-left transition-all hover:bg-gray-50',
                        isSelected(date) &&
                          'ring-2 ring-blue-500 ring-offset-2',
                        !isCurrentMonth(date) && 'opacity-40',
                        isToday(date) && 'border-blue-400',
                        {
                          'border-red-300 bg-red-50':
                            getDateIntensity(date) === 'critical',
                          'border-orange-300 bg-orange-50':
                            getDateIntensity(date) === 'high',
                          'border-yellow-300 bg-yellow-50':
                            getDateIntensity(date) === 'medium',
                          'border-green-300 bg-green-50':
                            getDateIntensity(date) === 'low',
                          'border-gray-200 bg-white':
                            getDateIntensity(date) === 'none',
                        },
                      )}
                    >
                      <span
                        className={cn(
                          'font-semibold',
                          isToday(date) && 'text-blue-600',
                        )}
                      >
                        {date.getDate()}
                      </span>
                      {loading[dateStr] && (
                        <Loader2 className="mt-1 h-3 w-3 animate-spin text-blue-500" />
                      )}
                      {!loading[dateStr] && dayEventsCount > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(dayEventsSeverity).map(
                            ([severity, count]) => {
                              if (count === 0) return null;
                              return (
                                <Badge
                                  variant="secondary"
                                  key={severity}
                                  className={cn(
                                    'px-0.5 py-0.5 text-[10px]',
                                    severity === '0' &&
                                      'bg-gray-200 text-gray-500',
                                    severity === '1' &&
                                      'bg-yellow-500 text-black',
                                    severity === '2' &&
                                      'bg-orange-500 text-white',
                                    severity === '3' && 'bg-red-500 text-white',
                                  )}
                                >
                                  {count}{' '}
                                  {severity === '1'
                                    ? 'Low'
                                    : severity === '2'
                                      ? 'High'
                                      : severity === '0'
                                        ? 'Unknown'
                                        : 'Critical'}
                                </Badge>
                              );
                            },
                          )}
                        </div>
                      )}
                    </Button>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
        <div className="sticky top-0 mb-4 h-fit w-full space-y-4 xl:w-96">
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl">
                <Activity className="h-6 w-6" />
                {selectedDate.toLocaleDateString('en-US', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedDateEvents.length > 0 ? (
                <div className="flex h-full flex-col">
                  <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4 text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {selectedDateEvents.length}
                    </div>
                    <div className="text-xs font-medium text-blue-500">
                      Total Events
                    </div>
                  </div>
                  {loadingImages[selectedDate.toLocaleDateString('en-CA')] && (
                    <div className="mb-4 flex items-center gap-2 text-sm text-gray-600">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading images...
                    </div>
                  )}
                  <div className="flex-grow space-y-3 overflow-y-auto">
                    {paginatedDetailsEvents.map((event) => (
                      <div
                        key={event.id}
                        className="rounded-lg border p-3 transition-colors hover:bg-gray-50"
                      >
                        <div className="mb-2 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Camera className="h-4 w-4 text-blue-500" />
                            <span className="text-sm font-medium">
                              {event.machineName}
                            </span>
                          </div>
                          {event?.event_severity && (
                            <Badge
                              variant="outline"
                              className={cn(
                                'text-xs',
                                event.event_severity === '1' &&
                                  'border-yellow-500 bg-yellow-400 text-black',
                                event.event_severity === '2' &&
                                  'border-orange-600 bg-orange-500 text-white',
                                event.event_severity === '3' &&
                                  'border-red-700 bg-red-600 text-white',
                              )}
                            >
                              {event.event_severity === '1'
                                ? 'Low'
                                : event.event_severity === '2'
                                  ? 'High'
                                  : 'Critical'}
                            </Badge>
                          )}
                        </div>
                        <div className="text-xs text-gray-600">
                          Time:{' '}
                          <span className="font-medium">
                            {new Date(event.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="mt-3 grid grid-cols-2 gap-2">
                          {event.croppedImageUrl && (
                            <div
                              className="cursor-pointer"
                              onClick={() =>
                                setModalImage({
                                  url: event.croppedImageUrl!,
                                  label: 'Cropped',
                                })
                              }
                            >
                              <Image
                                width={100}
                                height={100}
                                src={event.croppedImageUrl}
                                alt="Cropped"
                                className="h-24 w-full rounded border object-cover"
                              />
                            </div>
                          )}
                          {event.fullImageUrl && (
                            <div
                              className="cursor-pointer"
                              onClick={() =>
                                setModalImage({
                                  url: event.fullImageUrl!,
                                  label: 'Full',
                                })
                              }
                            >
                              <Image
                                width={100}
                                height={100}
                                src={event.fullImageUrl}
                                alt="Full"
                                className="h-24 w-full rounded border object-cover"
                              />
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  <Pagination
                    currentPage={detailsCurrentPage}
                    totalPages={totalDetailsPages}
                    onPageChange={setDetailsCurrentPage}
                  />
                </div>
              ) : loading[selectedDate.toLocaleDateString('en-CA')] ? (
                <div className="py-12 text-center text-gray-500">
                  <Loader2 className="mx-auto mb-4 h-16 w-16 animate-spin opacity-30" />
                  <p>Loading events...</p>
                </div>
              ) : (
                <div className="py-12 text-center text-gray-500">
                  <Activity className="mx-auto mb-4 h-16 w-16 opacity-30" />
                  <p className="text-lg font-medium">No events recorded</p>
                  <p className="text-sm">
                    {areaFilter
                      ? 'No events for this date in the selected area'
                      : 'No events found for this date'}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {showMapFilter && (
        <MapFilter
          machines={machines}
          onAreaSelect={setAreaFilter}
          onClose={() => setShowMapFilter(false)}
          selectedBounds={areaFilter}
        />
      )}
    </>
  );
}
