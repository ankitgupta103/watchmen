'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  Camera,
  ChevronLeft,
  ChevronRight,
  Filter,
  Loader2,
  X,
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

const MapFilter = dynamic(() => import('./map-filter'), {
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

  // Simplified state - just store events by date string
  const [events, setEvents] = useState<Record<string, ProcessedEvent[]>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [loadingImages, setLoadingImages] = useState<Record<string, boolean>>(
    {},
  );
  const [error, setError] = useState<string | null>(null);

  // Filter machines based on selected area
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

  // Simple function to fetch events for a single date
  const fetchEventsForDate = useCallback(
    async (date: Date) => {
      if (!token) return;

      const dateStr = date.toLocaleDateString('en-CA');

      // Skip if already loading or loaded
      if (loading[dateStr] || events[dateStr]) return;

      setLoading((prev) => ({ ...prev, [dateStr]: true }));
      setError(null);

      try {
        const machinesToCheck = areaFilter ? filteredMachines : machines;
        const allEvents: ProcessedEvent[] = [];

        // Fetch events for each machine for this date
        for (const machine of machinesToCheck) {
          try {
            const result = await fetcherClient<{
              success: boolean;
              events?: S3EventData[];
              error?: string;
            }>(`${API_BASE_URL}/s3-events/fetch-events/`, token, {
              method: 'POST',
              body: {
                org_id: orgId,
                date: dateStr,
                machine_id: machine.id,
              },
            });

            if (result?.success && result.events) {
              const processedEvents: ProcessedEvent[] = result.events.map(
                (event, index) => ({
                  ...event,
                  id: `${machine.id}-${dateStr}-${index}`,
                  machineId: machine.id,
                  machineName: machine.name,
                  timestamp: event.timestamp
                    ? new Date(event.timestamp)
                    : new Date(dateStr + 'T12:00:00'),
                  imagesLoaded: false,
                }),
              );

              allEvents.push(...processedEvents);
            }
          } catch (err) {
            console.warn(
              `Failed to fetch events for machine ${machine.id} on ${dateStr}:`,
              err,
            );
          }
        }

        setEvents((prev) => ({ ...prev, [dateStr]: allEvents }));
      } catch (err) {
        console.error('Error fetching events for date:', dateStr, err);
        setError(`Failed to fetch events for ${dateStr}`);
      } finally {
        setLoading((prev) => ({ ...prev, [dateStr]: false }));
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [token, orgId, areaFilter, filteredMachines, machines],
  );

  // Simple function to fetch images for events
  const fetchImagesForEvents = useCallback(
    async (dateStr: string, eventList: ProcessedEvent[]) => {
      if (!token || !eventList.length) return;

      // Skip if already loading images for this date
      if (loadingImages[dateStr]) return;

      setLoadingImages((prev) => ({ ...prev, [dateStr]: true }));

      try {
        const updatedEvents = await Promise.all(
          eventList.map(async (event) => {
            if (event.imagesLoaded) return event;

            try {
              const imageResult = await fetcherClient<{
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
              console.warn('Failed to fetch images for event:', event.id, err);
            }

            return { ...event, imagesLoaded: true }; // Mark as loaded even if failed
          }),
        );

        setEvents((prev) => ({ ...prev, [dateStr]: updatedEvents }));
      } catch (err) {
        console.error('Error fetching images for date:', dateStr, err);
      } finally {
        setLoadingImages((prev) => ({ ...prev, [dateStr]: false }));
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [token],
  );

  // Get calendar days for current month
  const getCalendarDays = useCallback(() => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());

    const days = [];
    const current = new Date(startDate);

    for (let i = 0; i < 42; i++) {
      days.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }

    return days;
  }, [currentMonth]);

  // Clear events when area filter changes
  useEffect(() => {
    setEvents({});
    setLoading({});
    setLoadingImages({});
    setError(null);
  }, [areaFilter]);

  // Fetch events for all visible days when month changes
  useEffect(() => {
    if (!token) return;

    const days = getCalendarDays();
    const currentMonthDays = days.filter(
      (day) =>
        day.getMonth() === currentMonth.getMonth() &&
        day.getFullYear() === currentMonth.getFullYear(),
    );

    // Fetch events for each day in the current month
    currentMonthDays.forEach((day) => {
      fetchEventsForDate(day);
    });
  }, [currentMonth, fetchEventsForDate, token, getCalendarDays]);

  // Fetch images for selected date events
  useEffect(() => {
    const dateStr = selectedDate.toLocaleDateString('en-CA');
    const dayEvents = events[dateStr];

    if (
      dayEvents &&
      dayEvents.length > 0 &&
      !dayEvents.every((e) => e.imagesLoaded)
    ) {
      fetchImagesForEvents(dateStr, dayEvents);
    }
  }, [selectedDate, events, fetchImagesForEvents]);

  const calendarDays = getCalendarDays();
  const selectedDateStr = selectedDate.toLocaleDateString('en-CA');
  const selectedDateEvents = events[selectedDateStr] || [];

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
    const dateStr = date.toLocaleDateString('en-CA');
    const dayEvents = events[dateStr] || [];
    const count = dayEvents.length;

    if (count > 10) return 'critical';
    if (count > 5) return 'high';
    if (count > 2) return 'medium';
    if (count > 0) return 'low';
    return 'none';
  };

  const handleAreaSelect = (bounds: MapBounds | null) => {
    setAreaFilter(bounds);
  };

  const isLoadingAny = Object.values(loading).some(Boolean);

  return (
    <>
      {/* Modal for image preview */}
      {modalImage && (
        <div
          className="bg-opacity-70 fixed inset-0 z-50 flex items-center justify-center bg-black"
          onClick={() => setModalImage(null)}
        >
          <div
            className="relative mx-4 w-full max-w-3xl"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="absolute top-2 right-2 z-10 rounded-full bg-white p-1 shadow hover:bg-gray-100"
              onClick={() => setModalImage(null)}
              aria-label="Close"
            >
              <X className="h-6 w-6 text-gray-700" />
            </button>
            <div className="flex flex-col items-center justify-center rounded-lg bg-white p-4">
              <Image
                src={modalImage.url}
                alt={modalImage.label}
                width={800}
                height={600}
                className="max-h-[80vh] w-auto rounded object-contain"
              />
              <div className="mt-2 text-sm text-gray-700">
                {modalImage.label}
              </div>
            </div>
          </div>
        </div>
      )}
      <div className="relative flex flex-col gap-4 overflow-y-auto xl:flex-row">
        {/* Error Banner */}
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3">
            <div className="flex items-center gap-2">
              <div className="text-sm text-red-800">
                <strong>Error:</strong> {error}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setError(null)}
                className="text-red-600 hover:text-red-800"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Calendar */}
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
                    className="flex items-center gap-2"
                  >
                    <Filter className="h-4 w-4" />
                    {areaFilter
                      ? `Filtered (${filteredMachines.length} machines)`
                      : 'Map Filter'}
                  </Button>
                  {isLoadingAny && (
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading events...
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
              {/* Filter Status Banner */}
              {areaFilter && (
                <div className="mb-4 flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50 p-3">
                  <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4 text-blue-600" />
                    <span className="text-sm text-blue-800">
                      Showing events from {filteredMachines.length} of{' '}
                      {machines.length} machines in selected area
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setAreaFilter(null)}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    Clear filter
                  </Button>
                </div>
              )}

              {/* Weekday Headers */}
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

              {/* Calendar Grid */}
              <div className="grid grid-cols-7 gap-2">
                {calendarDays.map((date, index) => {
                  const dateStr = date.toLocaleDateString('en-CA');
                  const dayEvents = events[dateStr] || [];
                  const intensity = getDateIntensity(date);
                  const isLoadingDate = loading[dateStr];

                  return (
                    <Button
                      key={index}
                      onClick={() => setSelectedDate(date)}
                      className={cn(
                        'group text-primary relative flex h-24 w-full flex-col items-start justify-start rounded-lg border-2 border-gray-200 bg-white p-1 text-left transition-all duration-200 hover:bg-gray-50',
                        isSelected(date) &&
                          'ring-2 ring-blue-500 ring-offset-2',
                        !isCurrentMonth(date) && 'opacity-40',
                        isToday(date) && 'ring-1 ring-blue-400',
                        intensity === 'critical' && 'border-red-300 bg-red-50',
                        intensity === 'high' &&
                          'border-orange-300 bg-orange-50',
                        intensity === 'medium' &&
                          'border-yellow-300 bg-yellow-50',
                        intensity === 'low' && 'border-green-300 bg-green-50',
                      )}
                    >
                      <span
                        className={cn(
                          'font-semibold',
                          !isCurrentMonth(date) && 'text-gray-400',
                          isToday(date) && 'text-blue-600',
                        )}
                      >
                        {date.getDate()}
                      </span>

                      {/* Loading indicator */}
                      {isLoadingDate && (
                        <div className="mt-1">
                          <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
                        </div>
                      )}

                      {/* Activity Badge */}
                      {!isLoadingDate && dayEvents.length > 0 && (
                        <div className="mt-1 flex w-full flex-col items-start gap-1">
                          <Badge
                            variant={
                              intensity === 'critical'
                                ? 'destructive'
                                : intensity === 'high'
                                  ? 'secondary'
                                  : intensity === 'medium'
                                    ? 'outline'
                                    : 'default'
                            }
                            className="h-auto w-full px-1 py-0.5 text-[10px]"
                          >
                            {dayEvents.length} Event
                            {dayEvents.length > 1 ? 's' : ''}
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

        {/* Details Panel */}
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
                <div className="space-y-6">
                  {/* Filter Status in Details */}
                  {areaFilter && (
                    <div className="flex items-center gap-1 rounded border border-blue-200 bg-blue-50 p-2 text-xs text-blue-800">
                      <Filter className="h-3 w-3" />
                      <span>
                        Filtered view - showing events from selected area only
                      </span>
                    </div>
                  )}

                  {/* Summary Stats */}
                  <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {selectedDateEvents.length}
                    </div>
                    <div className="text-xs font-medium text-blue-500">
                      Total Events
                    </div>
                  </div>

                  {/* Loading images indicator */}
                  {loadingImages[selectedDateStr] && (
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading images...
                    </div>
                  )}

                  {/* Event Details */}
                  <div className="max-h-80 space-y-3 overflow-y-auto">
                    <div className="flex items-center justify-between">
                      <h4 className="text-lg font-semibold">Event Timeline</h4>
                      <span className="text-xs text-gray-500">
                        {selectedDateEvents.length} events
                      </span>
                    </div>
                    {selectedDateEvents
                      .sort(
                        (a, b) =>
                          new Date(b.timestamp).getTime() -
                          new Date(a.timestamp).getTime(),
                      )
                      .map((event) => (
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
                            <Badge variant="outline" className="text-xs">
                              Event
                            </Badge>
                          </div>

                          <div className="space-y-2 text-xs text-gray-600">
                            <div>
                              Event:{' '}
                              <span className="font-medium">
                                {event.eventstr}
                              </span>
                            </div>
                            <div>
                              Time:{' '}
                              <span className="font-medium">
                                {new Date(event.timestamp).toLocaleTimeString()}
                              </span>
                            </div>
                            <div>
                              Machine ID:{' '}
                              <span className="font-medium">
                                {event.machineId}
                              </span>
                            </div>
                          </div>

                          {/* Image Display */}
                          <div className="mt-3 grid grid-cols-2 gap-2">
                            <div
                              className="cursor-pointer space-y-1"
                              onClick={() =>
                                setModalImage({
                                  url: event.croppedImageUrl!,
                                  label: 'Cropped',
                                })
                              }
                            >
                              <p className="text-xs text-gray-500">Cropped</p>
                              <Image
                                width={100}
                                height={100}
                                src={event?.croppedImageUrl ?? ''}
                                alt="Cropped event image"
                                className="h-full w-full rounded border object-cover"
                              />
                            </div>
                            <div
                              className="cursor-pointer space-y-1"
                              onClick={() =>
                                setModalImage({
                                  url: event.fullImageUrl!,
                                  label: 'Full',
                                })
                              }
                            >
                              <p className="text-xs text-gray-500">Full</p>
                              <Image
                                width={100}
                                height={100}
                                src={event?.fullImageUrl ?? ''}
                                alt="Full event image"
                                className="h-full w-full rounded border object-cover"
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ) : loading[selectedDateStr] ? (
                <div className="py-12 text-center text-gray-500">
                  <Loader2 className="mx-auto mb-4 h-16 w-16 animate-spin opacity-30" />
                  <p className="text-lg font-medium">Loading events...</p>
                </div>
              ) : (
                <div className="py-12 text-center text-gray-500">
                  <Activity className="mx-auto mb-4 h-16 w-16 opacity-30" />
                  <p className="text-lg font-medium">No events recorded</p>
                  <p className="text-sm">
                    {areaFilter
                      ? 'No events found in the selected area for this date'
                      : 'No events found for this date'}
                  </p>
                  {areaFilter && machines.length > filteredMachines.length && (
                    <Button
                      variant="link"
                      size="sm"
                      onClick={() => setAreaFilter(null)}
                      className="mt-2 text-blue-600"
                    >
                      Clear area filter to see all events
                    </Button>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Map Filter Modal */}
      {showMapFilter && (
        <MapFilter
          machines={machines}
          onAreaSelect={handleAreaSelect}
          onClose={() => setShowMapFilter(false)}
          selectedBounds={areaFilter}
        />
      )}
    </>
  );
}
