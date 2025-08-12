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
import { Machine, S3EventData } from '@/lib/types/machine';
import { cn } from '@/lib/utils';
import { getPresignedUrl } from '@/lib/utils/presigned-url';

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

interface ProcessedEvent extends Omit<S3EventData, 'timestamp'> {
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

  // Refs to hold current state for use in callbacks and for aborting fetches
  const eventsRef = useRef(events);
  eventsRef.current = events;
  const loadingRef = useRef(loading);
  loadingRef.current = loading;
  const imageFetchControllerRef = useRef<AbortController | null>(null);

  // Pagination state
  const [detailsCurrentPage, setDetailsCurrentPage] = useState(1);
  const eventsPerPage = 5;

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
    async (date: Date, signal: AbortSignal) => {
      if (!token) return;
      const dateStr = date.toLocaleDateString('en-CA');
      // More robust check to prevent any re-fetching
      if (dateStr in eventsRef.current) {
        return;
      }

      setLoading((prev) => ({ ...prev, [dateStr]: true }));
      setEvents((prev) => ({ ...prev, [dateStr]: [] })); // Initialize to show loading and prevent refetch

      try {
        const machinesToCheck = areaFilter ? filteredMachines : machines;
        const fetchPromises = machinesToCheck.map((machine) =>
          fetcherClient<{
            success: boolean;
            events?: S3EventData[];
          }>(`${API_BASE_URL}/s3-events/fetch-events/`, token, {
            method: 'POST',
            body: { org_id: orgId, date: dateStr, machine_id: machine.id },
            signal,
          })
            .then((result) => {
              if (result?.success && result.events) {
                const newEvents = result.events.map((event, index) => ({
                  ...event,
                  id: `${machine.id}-${dateStr}-${index}`,
                  machineId: machine.id,
                  machineName: machine.name,
                  timestamp: event.timestamp
                    ? new Date(Number(event.timestamp) * 1000)
                    : new Date(dateStr + 'T12:00:00'),
                  imagesLoaded: false,
                }));
                setEvents((prev) => ({
                  ...prev,
                  [dateStr]: [...(prev[dateStr] || []), ...newEvents],
                }));
              }
            })
            .catch((err) => {
              if (err.name !== 'AbortError') {
                console.warn(
                  `Fetch failed for machine ${machine.id} on ${dateStr} ${err}`,
                );
              }
            }),
        );
        await Promise.allSettled(fetchPromises);
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          console.error(`Failed to fetch events for ${dateStr}`, err);
        }
      } finally {
        if (!signal.aborted) {
          setLoading((prev) => ({ ...prev, [dateStr]: false }));
        }
      }
    },
    [token, orgId, areaFilter, filteredMachines, machines],
  );

  const fetchImagesForEvents = useCallback(
    async (
      dateStr: string,
      eventList: ProcessedEvent[],
      signal: AbortSignal,
    ) => {
      const eventsToFetch = eventList.filter(
        (e) => (e.image_c_key || e.original_image_path) && !e.imagesLoaded,
      );
      if (!token || eventsToFetch.length === 0) return;

      setLoadingImages((prev) => ({ ...prev, [dateStr]: true }));
      try {
        const imagePromises = eventsToFetch.map(async (event) => {
          if (signal.aborted) return;
          
          try {
            let croppedImageUrl: string | null = null;
            let fullImageUrl: string | null = null;

            // Get presigned URL for cropped image if available
            if (event.image_c_key) {
              croppedImageUrl = await getPresignedUrl(event.image_c_key, token);
            }

            // Get presigned URL for full image if available
            if (event.image_f_key) {
              fullImageUrl = await getPresignedUrl(event.image_f_key, token);
            }

            // If no specific keys, try to get from original_image_path
            if (!croppedImageUrl && !fullImageUrl && event.original_image_path) {
              fullImageUrl = await getPresignedUrl(event.original_image_path, token);
            }

            const updatedEvent = {
              ...event,
              croppedImageUrl: croppedImageUrl || undefined,
              fullImageUrl: fullImageUrl || undefined,
              imagesLoaded: true,
            };

            setEvents((prev) => {
              const newDayEvents = [...(prev[dateStr] || [])];
              const index = newDayEvents.findIndex((e) => e.id === event.id);
              if (index !== -1) newDayEvents[index] = updatedEvent;
              return { ...prev, [dateStr]: newDayEvents };
            });
          } catch (err) {
            if (err instanceof Error && err.name !== 'AbortError') {
              console.warn(
                `Image fetch failed for event: ${event.id} ${err}`,
              );
            }
            // Mark as loaded even if failed to prevent infinite retries
            const updatedEvent = { ...event, imagesLoaded: true };
            setEvents((prev) => {
              const newDayEvents = [...(prev[dateStr] || [])];
              const index = newDayEvents.findIndex(
                (e) => e.id === event.id,
              );
              if (index !== -1) newDayEvents[index] = updatedEvent;
              return { ...prev, [dateStr]: newDayEvents };
            });
          }
        });

        await Promise.allSettled(imagePromises);
      } finally {
        if (!signal.aborted) {
          setLoadingImages((prev) => ({ ...prev, [dateStr]: false }));
        }
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

  // Fetch events in sequential batches, from last day of month to first.
  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;

    const fetchInBatches = async () => {
      if (!token) return;
      const daysInMonth = getCalendarDays().filter(
        (day) => day.getMonth() === currentMonth.getMonth(),
      );

      const BATCH_SIZE = 10;
      for (let i = daysInMonth.length - 1; i >= 0; i -= BATCH_SIZE) {
        if (signal.aborted) break;
        const batchDays = daysInMonth
          .slice(Math.max(0, i - BATCH_SIZE + 1), i + 1)
          .reverse();

        const batchPromises = batchDays.map((day) => {
          if (day <= new Date()) {
            return fetchEventsForDate(day, signal);
          }
          return Promise.resolve();
        });
        await Promise.all(batchPromises);
      }
    };

    fetchInBatches();

    return () => {
      controller.abort();
    };
  }, [currentMonth, fetchEventsForDate, token, getCalendarDays]);

  const selectedDateEvents = useMemo(
    () =>
      (events[selectedDate.toLocaleDateString('en-CA')] || []).sort(
        (a, b) =>
          new Date(Number(b.timestamp) * 1000).getTime() - new Date(Number(a.timestamp) * 1000).getTime(),
      ),
    [events, selectedDate],
  );

  const paginatedDetailsEvents = useMemo(() => {
    const startIndex = (detailsCurrentPage - 1) * eventsPerPage;
    return selectedDateEvents.slice(startIndex, startIndex + eventsPerPage);
  }, [selectedDateEvents, detailsCurrentPage]);

  // Fetch images for the visible page, with cancellation on page change.
  useEffect(() => {
    // Abort previous image fetches before starting new ones
    if (imageFetchControllerRef.current) {
      imageFetchControllerRef.current.abort();
    }

    if (paginatedDetailsEvents.length > 0) {
      const controller = new AbortController();
      imageFetchControllerRef.current = controller;
      const dateStr = selectedDate.toLocaleDateString('en-CA');
      fetchImagesForEvents(dateStr, paginatedDetailsEvents, controller.signal);
    }

    return () => {
      // Cleanup when the component unmounts or selectedDate changes
      if (imageFetchControllerRef.current) {
        imageFetchControllerRef.current.abort();
      }
    };
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
      {/* Main Calendar */}
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

                  return (
                    <Button
                      key={index}
                      onClick={() => setSelectedDate(date)}
                      className={cn(
                        'text-primary relative flex h-28 w-full flex-col items-start justify-start rounded-lg border-2 px-1 py-0.5 text-left transition-all hover:bg-gray-50',
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
                          <Badge
                            variant="secondary"
                            className="px-1 py-0.5 text-[10px] bg-blue-200 text-blue-700"
                          >
                            {dayEventsCount} Events
                          </Badge>
                        </div>
                      )}
                    </Button>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Side Panel */}
        <div className="sticky top-0 mb-4 h-fit w-full space-y-4 xl:w-[420px]">
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
                          <Badge
                            variant="outline"
                            className="text-xs border-gray-300 bg-gray-100 text-gray-700"
                          >
                            Event
                          </Badge>
                        </div>
                        <div className="text-xs text-gray-600">
                          Time:{' '}
                          <span className="font-medium">
                            {new Date(Number(event.timestamp) * 1000).toLocaleTimeString()}
                          </span>
                        </div>
                        {event.eventstr && (
                          <div className="text-xs text-gray-600 mt-1">
                            Event: <span className="font-medium">{event.eventstr}</span>
                          </div>
                        )}
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
