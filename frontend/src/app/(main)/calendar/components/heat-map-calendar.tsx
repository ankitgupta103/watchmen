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

// S3 Event data structure
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
  imagesFetched: boolean;
  fetchingImages: boolean;
}

interface DayEventData {
  [date: string]: ProcessedEvent[]; // YYYY-MM-DD format
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
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(
    new Date(),
  );
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [showMapFilter, setShowMapFilter] = useState(false);
  const [areaFilter, setAreaFilter] = useState<MapBounds | null>(null);
  const [eventData, setEventData] = useState<DayEventData>({});
  const [loading, setLoading] = useState(false);
  const [loadedMonths, setLoadedMonths] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  // Filter machines based on selected area
  const filteredMachines = useMemo(() => {
    if (!areaFilter) return machines;

    const filtered = machines.filter(
      (machine) =>
        machine.last_location.lat >= areaFilter.south &&
        machine.last_location.lat <= areaFilter.north &&
        machine.last_location.lng >= areaFilter.west &&
        machine.last_location.lng <= areaFilter.east,
    );

    return filtered;
  }, [machines, areaFilter]);

  // Fetch images from Django backend using your EventImageStatusView
  const fetchEventImages = useCallback(
    async (imageKeys: { image_c_key: string; image_f_key: string }) => {
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
    },
    [token],
  );

  // Function to fetch events from S3 for a specific date
  const fetchS3EventsForDate = useCallback(
    async (date: Date): Promise<ProcessedEvent[]> => {
      if (!token) {
        console.error('No authentication token available');
        return [];
      }

      const dateStr = date.toISOString().split('T')[0];
      const events: ProcessedEvent[] = [];

      try {
        const machinesToCheck = areaFilter ? filteredMachines : machines;

        const fetchPromises = machinesToCheck.map(async (machine) => {
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

            if (!result?.success) {
              if (result?.error && !result.error.includes('404')) {
                console.error(`Error for machine ${machine.id}:`, result.error);
              }
              return [];
            }

            const s3Events: S3EventData[] = result.events || [];

            const processedEvents: ProcessedEvent[] = s3Events.map(
              (s3Event, index) => ({
                ...s3Event,
                id: `${machine.id}-${dateStr}-${index}`,
                machineId: machine.id,
                machineName: machine.name,
                timestamp: s3Event.timestamp
                  ? new Date(s3Event.timestamp)
                  : new Date(dateStr + 'T12:00:00'),
                imagesFetched: false,
                fetchingImages: false,
              }),
            );

            return processedEvents;
          } catch (error) {
            console.error(
              `Error fetching events for machine ${machine.id}:`,
              error,
            );
            return [];
          }
        });

        const allMachineEvents = await Promise.all(fetchPromises);
        events.push(...allMachineEvents.flat());
      } catch (error) {
        console.error('Error fetching S3 events for date:', date, error);
        setError(
          `Failed to fetch events: ${error instanceof Error ? error.message : 'Unknown error'}`,
        );
      }

      return events;
    },
    [token, orgId, areaFilter, filteredMachines, machines],
  );

  // Function to fetch events for entire month (optimized using date range API)
  const fetchMonthEvents = useCallback(
    async (year: number, month: number) => {
      if (!token) {
        console.error('No authentication token available');
        return;
      }

      const monthKey = `${year}-${month}`;
      if (loadedMonths.has(monthKey)) return;

      setLoading(true);
      setError(null);

      try {
        const startDate = new Date(year, month - 1, 1);
        const endDate = new Date(year, month, 0);

        const startDateStr = startDate.toISOString().split('T')[0];
        const endDateStr = endDate.toISOString().split('T')[0];

        const machinesToCheck = areaFilter ? filteredMachines : machines;
        const machineIds = machinesToCheck.map((m) => m.id);

        if (machineIds.length === 0) {
          setLoadedMonths((prev) => new Set([...prev, monthKey]));
          setLoading(false);
          return;
        }

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
            machine_ids: machineIds,
          },
        });

        if (!result?.success) {
          console.warn(
            'Month range API failed, falling back to individual dates',
          );
          await fetchMonthEventsIndividually(year, month);
          return;
        }

        const dateEvents = result.date_events || {};

        const monthEventData: DayEventData = {};

        Object.entries(dateEvents).forEach(([dateStr, dayEvents]) => {
          const processedEvents: ProcessedEvent[] = (
            dayEvents as S3EventData[]
          ).map((s3Event, index) => {
            const machine = machinesToCheck.find(
              (m) => m.id === s3Event.machineId,
            );
            return {
              ...s3Event,
              id: `${s3Event.machineId}-${dateStr}-${index}`,
              machineId: s3Event.machineId || 0,
              machineName: machine?.name || `Machine ${s3Event.machineId}`,
              timestamp: s3Event.timestamp
                ? new Date(s3Event.timestamp)
                : new Date(dateStr + 'T12:00:00'),
              imagesFetched: false,
              fetchingImages: false,
            };
          });

          if (processedEvents.length > 0) {
            monthEventData[dateStr] = processedEvents;
          }
        });

        setEventData((prev) => ({
          ...prev,
          ...monthEventData,
        }));

        setLoadedMonths((prev) => new Set([...prev, monthKey]));
      } catch (error) {
        console.error('Error fetching month events:', error);
        setError(
          `Failed to fetch month events: ${error instanceof Error ? error.message : 'Unknown error'}`,
        );
        await fetchMonthEventsIndividually(year, month);
      } finally {
        setLoading(false);
      }
    },
    [token, orgId, areaFilter, filteredMachines, machines, loadedMonths],
  );

  // Fallback method for individual date fetching
  const fetchMonthEventsIndividually = useCallback(
    async (year: number, month: number) => {
      try {
        const startDate = new Date(year, month - 1, 1);
        const endDate = new Date(year, month, 0);

        const dates: Date[] = [];
        const current = new Date(startDate);

        while (current <= endDate) {
          dates.push(new Date(current));
          current.setDate(current.getDate() + 1);
        }

        const fetchPromises = dates.map(async (date) => {
          const events = await fetchS3EventsForDate(date);
          const dateStr = date.toISOString().split('T')[0];
          return { dateStr, events };
        });

        const results = await Promise.all(fetchPromises);

        const monthEventData: DayEventData = {};
        results.forEach(({ dateStr, events }) => {
          if (events.length > 0) {
            monthEventData[dateStr] = events;
          }
        });

        setEventData((prev) => ({
          ...prev,
          ...monthEventData,
        }));

        const monthKey = `${year}-${month}`;
        setLoadedMonths((prev) => new Set([...prev, monthKey]));
      } catch (error) {
        console.error('Error in fallback month fetching:', error);
        setError(
          `Failed to fetch events: ${error instanceof Error ? error.message : 'Unknown error'}`,
        );
      }
    },
    [fetchS3EventsForDate],
  );

  // Fetch images for events
  const fetchImagesForEvents = useCallback(
    async (events: ProcessedEvent[]) => {
      const fetchPromises = events.map(async (event) => {
        if (event.imagesFetched || event.fetchingImages) return event;

        const updatedEvent = { ...event, fetchingImages: true };

        try {
          const imageUrls = await fetchEventImages({
            image_c_key: event.image_c_key,
            image_f_key: event.image_f_key,
          });

          return {
            ...updatedEvent,
            croppedImageUrl: imageUrls?.croppedImageUrl,
            fullImageUrl: imageUrls?.fullImageUrl,
            imagesFetched: true,
            fetchingImages: false,
          };
        } catch (error) {
          console.error('Error fetching images for event:', event.id, error);
          return {
            ...updatedEvent,
            fetchingImages: false,
          };
        }
      });

      return Promise.all(fetchPromises);
    },
    [fetchEventImages],
  );

  // Clear loaded months when area filter changes
  useEffect(() => {
    setLoadedMonths(new Set());
    setEventData({});
    setError(null);
  }, [areaFilter]);

  // Load events when month changes
  useEffect(() => {
    if (token) {
      const year = currentMonth.getFullYear();
      const month = currentMonth.getMonth() + 1;
      fetchMonthEvents(year, month);
    }
  }, [currentMonth, fetchMonthEvents, token]);

  // Fetch images when selectedDate changes
  useEffect(() => {
    if (selectedDate && token) {
      const dateStr = selectedDate.toISOString().split('T')[0];
      const dayEvents = eventData[dateStr];

      if (dayEvents && dayEvents.length > 0) {
        fetchImagesForEvents(dayEvents).then((updatedEvents) => {
          setEventData((prev) => ({
            ...prev,
            [dateStr]: updatedEvents,
          }));
        });
      }
    }
  }, [selectedDate, fetchImagesForEvents, token, eventData]);

  // Process event data to create heat map data
  const heatMapData = useMemo(() => {
    const activityMap = new Map<
      string,
      {
        date: Date;
        eventCount: number;
        events: ProcessedEvent[];
        intensity: 'none' | 'low' | 'medium' | 'high' | 'critical';
      }
    >();

    Object.entries(eventData).forEach(([dateStr, dayEvents]) => {
      const date = new Date(dateStr + 'T00:00:00');
      const dateKey = date.toDateString();

      const eventCount = dayEvents.length;
      let intensity: 'none' | 'low' | 'medium' | 'high' | 'critical' = 'none';

      if (eventCount > 10) {
        intensity = 'critical';
      } else if (eventCount > 5) {
        intensity = 'high';
      } else if (eventCount > 2) {
        intensity = 'medium';
      } else if (eventCount > 0) {
        intensity = 'low';
      }

      if (eventCount > 0) {
        activityMap.set(dateKey, {
          date,
          eventCount,
          events: dayEvents,
          intensity,
        });
      }
    });

    return activityMap;
  }, [eventData]);

  // Get calendar days for current month
  const getCalendarDays = () => {
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
  };

  const calendarDays = getCalendarDays();
  const selectedDateActivity = selectedDate
    ? heatMapData.get(selectedDate.toDateString())
    : null;

  const navigateMonth = (direction: 'prev' | 'next') => {
    setCurrentMonth((prev) => {
      const newDate = new Date(prev);
      newDate.setMonth(prev.getMonth() + (direction === 'next' ? 1 : -1));
      return newDate;
    });
  };

  const isCurrentMonth = (date: Date) => {
    return date.getMonth() === currentMonth.getMonth();
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const isSelected = (date: Date) => {
    return selectedDate?.toDateString() === date.toDateString();
  };

  const handleAreaSelect = (bounds: MapBounds | null) => {
    setAreaFilter(bounds);
  };

  return (
    <>
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
                  {loading && (
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
                    disabled={loading}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigateMonth('next')}
                    disabled={loading}
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
                  const activity = heatMapData.get(date.toDateString());

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
                        activity &&
                          activity.intensity === 'critical' &&
                          'border-red-300 bg-red-50',
                        activity &&
                          activity.intensity === 'high' &&
                          'border-orange-300 bg-orange-50',
                        activity &&
                          activity.intensity === 'medium' &&
                          'border-yellow-300 bg-yellow-50',
                        activity &&
                          activity.intensity === 'low' &&
                          'border-green-300 bg-green-50',
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

                      {/* Activity Badge */}
                      {activity && (
                        <div className="mt-1 flex w-full flex-col items-start gap-1">
                          <Badge
                            variant={
                              activity.intensity === 'critical'
                                ? 'destructive'
                                : activity.intensity === 'high'
                                  ? 'secondary'
                                  : activity.intensity === 'medium'
                                    ? 'outline'
                                    : 'default'
                            }
                            className="h-auto w-full px-1 py-0.5 text-[10px]"
                          >
                            {activity.eventCount} Event
                            {activity.eventCount > 1 ? 's' : ''}
                          </Badge>
                        </div>
                      )}

                      {/* Filter indicator */}
                      {areaFilter && !activity && isCurrentMonth(date) && (
                        <div className="absolute right-1 bottom-1">
                          <div
                            className="h-1.5 w-1.5 rounded-full bg-blue-400"
                            title="Area filter active"
                          />
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
                {selectedDate
                  ? selectedDate.toLocaleDateString('en-US', {
                      weekday: 'long',
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })
                  : 'Select a Date'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedDateActivity ? (
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
                      {selectedDateActivity.eventCount}
                    </div>
                    <div className="text-xs font-medium text-blue-500">
                      Total Events
                    </div>
                  </div>

                  {/* Event Details */}
                  <div className="max-h-80 space-y-3 overflow-y-auto">
                    <div className="flex items-center justify-between">
                      <h4 className="text-lg font-semibold">Event Timeline</h4>
                      <span className="text-xs text-gray-500">
                        {selectedDateActivity.events.length} events
                      </span>
                    </div>
                    {selectedDateActivity.events
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
                          <div className="h-full w-full">
                            <div className="grid grid-cols-2 gap-2">
                              <div className="h-full w-full space-y-2">
                                <p className="text-xs text-gray-500">
                                  Cropped
                                </p>
                                <Image
                                  width={100}
                                  height={100}
                                  src={event?.croppedImageUrl ?? ''}
                                  alt="Cropped event image"
                                  className="h-full w-full rounded border object-contain"
                                />
                              </div>
                              <div className="h-full w-full">
                                <p className="mb-1 text-xs text-gray-500">
                                  Full
                                </p>
                                <Image
                                  width={100}
                                  height={100}
                                  src={event?.fullImageUrl ?? ''}
                                  alt="Full event image"
                                  className="h-full w-full rounded border object-contain"
                                />
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ) : (
                <div className="py-12 text-center text-gray-500">
                  <Activity className="mx-auto mb-4 h-16 w-16 opacity-30" />
                  <p className="text-lg font-medium">No events recorded</p>
                  <p className="text-sm">
                    {areaFilter
                      ? 'No events found in the selected area for this date'
                      : 'Select a date to view events'}
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
