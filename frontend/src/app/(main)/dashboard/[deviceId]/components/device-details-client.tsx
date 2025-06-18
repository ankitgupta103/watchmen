'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useMachineStats } from '@/hooks/use-machine-stats';
import useToken from '@/hooks/use-token';
import {
  Activity,
  Calendar,
  Camera,
  Info,
  Loader2,
  MapPin,
  Server,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';
import Image from 'next/image';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { Machine } from '@/lib/types/machine';
import { formatBufferSize } from '@/lib/utils';

import PageHeader from './page-header';

// S3 Event data structure (from heat map calendar)
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

interface DeviceDetailsClientProps {
  device: Machine;
  orgId: number;
}

export default function DeviceDetailsClient({
  device,
  orgId,
}: DeviceDetailsClientProps) {
  const { token } = useToken();
  const { data: machineStats, buffer } = useMachineStats(device.id);

  const [events, setEvents] = useState<ProcessedEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<'7' | '30' | '90'>('30');
  const [selectedEvent, setSelectedEvent] = useState<ProcessedEvent | null>(
    null,
  );

  // Fetch images from Django backend (from heat map calendar)
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

  // Fetch events for date range
  const fetchEventsForDateRange = useCallback(
    async (days: number) => {
      if (!token) {
        console.error('No authentication token available');
        return [];
      }

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
          console.warn('Date range API failed, trying individual dates');
          return await fetchEventsIndividually(days);
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

        return allEvents.sort(
          (a, b) =>
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
        );
      } catch (error) {
        console.error('Error fetching events for date range:', error);
        throw error;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [token, orgId, device.id],
  );

  // Fallback individual date fetching
  const fetchEventsIndividually = useCallback(
    async (days: number) => {
      const dates: Date[] = [];
      const current = new Date();

      for (let i = 0; i < days; i++) {
        const date = new Date(current);
        date.setDate(date.getDate() - i);
        dates.push(date);
      }

      const fetchPromises = dates.map(async (date) => {
        const dateStr = date.toISOString().split('T')[0];

        try {
          if (!token) {
            console.error('No authentication token available');
            return [];
          }

          const result = await fetcherClient<{
            success: boolean;
            events?: S3EventData[];
            error?: string;
          }>(`${API_BASE_URL}/s3-events/fetch-events/`, token, {
            method: 'POST',
            body: {
              org_id: orgId,
              date: dateStr,
              machine_id: device.id,
            },
          });

          if (!result?.success) {
            return [];
          }

          const s3Events: S3EventData[] = result.events || [];
          return s3Events.map((s3Event, index) => ({
            ...s3Event,
            id: `${device.id}-${dateStr}-${index}`,
            machineId: device.id,
            timestamp: s3Event.timestamp
              ? new Date(s3Event.timestamp)
              : new Date(dateStr + 'T12:00:00'),
            imagesFetched: false,
            fetchingImages: false,
          }));
        } catch (error) {
          console.error(`Error fetching events for ${dateStr}:`, error);
          return [];
        }
      });

      const results = await Promise.all(fetchPromises);
      const allEvents = results.flat();

      return allEvents.sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      );
    },
    [token, orgId, device.id],
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

  // Load events when component mounts or date range changes
  useEffect(() => {
    if (token) {
      setLoading(true);
      setError(null);

      fetchEventsForDateRange(parseInt(dateRange))
        .then(async (fetchedEvents) => {
          setEvents(fetchedEvents);

          // Fetch images for the first 10 events initially
          if (fetchedEvents.length > 0) {
            const eventsToFetchImages = fetchedEvents.slice(0, 10);
            const eventsWithImages =
              await fetchImagesForEvents(eventsToFetchImages);

            setEvents((prev) => {
              const updated = [...prev];
              eventsWithImages.forEach((eventWithImage) => {
                const index = updated.findIndex(
                  (e) => e.id === eventWithImage.id,
                );
                if (index !== -1) {
                  updated[index] = eventWithImage;
                }
              });
              return updated;
            });
          }
        })
        .catch((error) => {
          console.error('Error loading events:', error);
          setError(`Failed to load events: ${error.message}`);
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [token, dateRange, fetchEventsForDateRange, fetchImagesForEvents]);

  // Load more images when event is selected
  const handleEventSelect = useCallback(
    async (event: ProcessedEvent) => {
      setSelectedEvent(event);

      if (!event.imagesFetched && !event.fetchingImages) {
        const updatedEvent = await fetchImagesForEvents([event]);
        if (updatedEvent.length > 0) {
          setEvents((prev) =>
            prev.map((e) => (e.id === event.id ? updatedEvent[0] : e)),
          );
          setSelectedEvent(updatedEvent[0]);
        }
      }
    },
    [fetchImagesForEvents],
  );

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader deviceId={device.id.toString()} deviceName={device.name} />

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

      {/* Device Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-6 w-6" />
            Device Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="space-y-4">
              <div>
                <h1 className="mb-2 text-3xl font-bold">
                  {device.name.replace(/-/g, ' ')}
                </h1>
                <div className="mb-4 flex flex-wrap gap-2">
                  <Badge
                    variant={machineStats !== null ? 'default' : 'destructive'}
                    className="flex items-center gap-1 capitalize"
                  >
                    {machineStats !== null ? (
                      <Wifi className="h-3 w-3" />
                    ) : (
                      <WifiOff className="h-3 w-3" />
                    )}
                    {machineStats !== null ? 'Online' : 'Offline'}
                  </Badge>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-semibold text-gray-600">
                    Machine UID:
                  </span>
                  <p className="font-mono">{device.machine_uid}</p>
                </div>
                <div>
                  <span className="font-semibold text-gray-600">
                    Model UID:
                  </span>
                  <p className="font-mono">{device.model_uid}</p>
                </div>
                <div>
                  <span className="font-semibold text-gray-600">Owner:</span>
                  <p>{device.current_owner_name}</p>
                </div>
                <div>
                  <span className="font-semibold text-gray-600">Buffer:</span>
                  <p>{formatBufferSize(buffer)}</p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <h3 className="mb-2 flex items-center gap-2 font-semibold text-gray-600">
                  <Calendar className="h-4 w-4" />
                  Important Dates
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Manufacturing:</span>
                    <span>
                      {new Date(device.mfg_date).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Activation:</span>
                    <span>
                      {new Date(device.activation_date).toLocaleDateString()}
                    </span>
                  </div>
                  {device.end_of_service_date && (
                    <div className="flex justify-between">
                      <span>End of Service:</span>
                      <span>
                        {new Date(
                          device.end_of_service_date,
                        ).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <h3 className="mb-2 flex items-center gap-2 font-semibold text-gray-600">
                  <MapPin className="h-4 w-4" />
                  Location
                </h3>
                <div className="space-y-1 text-sm">
                  <div>
                    <span className="font-medium">Real-time:</span>{' '}
                    {machineStats?.message?.location?.lat?.toFixed(4) ??
                      device?.last_location?.lat?.toFixed(4) ??
                      'N/A'}
                    ,{' '}
                    {machineStats?.message?.location?.lng?.toFixed(4) ??
                      device?.last_location?.lng?.toFixed(4) ??
                      'N/A'}
                  </div>
                  <div>
                    <span className="font-medium">Last known:</span>{' '}
                    {device?.last_location?.lat?.toFixed(4) ?? 'N/A'},{' '}
                    {device?.last_location?.lng?.toFixed(4) ?? 'N/A'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Events Section */}
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
                onValueChange={(value: '7' | '30' | '90') =>
                  setDateRange(value)
                }
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
                  Loading...
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
            <div className="space-y-4">
              <div className="mb-4 text-sm text-gray-600">
                Found {events.length} events in the last {dateRange} days
              </div>

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Event</TableHead>
                    <TableHead>Images</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.slice(0, 50).map((event) => (
                    <TableRow key={event.id}>
                      <TableCell>
                        {new Date(event.timestamp).toLocaleString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{event.eventstr}</Badge>
                      </TableCell>
                      <TableCell>
                        {event.fetchingImages ? (
                          <div className="flex items-center gap-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm text-gray-500">
                              Loading...
                            </span>
                          </div>
                        ) : event.imagesFetched ? (
                          <div className="flex gap-2">
                            {event.croppedImageUrl && (
                              <Image
                                src={event.croppedImageUrl}
                                alt="Cropped"
                                width={40}
                                height={40}
                                className="rounded border object-cover"
                              />
                            )}
                            {event.fullImageUrl && (
                              <Image
                                src={event.fullImageUrl}
                                alt="Full"
                                width={40}
                                height={40}
                                className="rounded border object-cover"
                              />
                            )}
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <Camera className="h-4 w-4 text-gray-400" />
                            <span className="text-sm text-gray-500">
                              Available
                            </span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEventSelect(event)}
                        >
                          View Details
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {events.length > 50 && (
                <div className="py-4 text-center text-sm text-gray-500">
                  Showing first 50 events of {events.length} total
                </div>
              )}
            </div>
          ) : (
            <div className="py-12 text-center text-gray-500">
              <Activity className="mx-auto mb-4 h-16 w-16 opacity-30" />
              <p className="text-lg font-medium">No events found</p>
              <p className="text-sm">
                No events recorded for this device in the last {dateRange} days
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Event Details Modal */}
      {selectedEvent && (
        <div className="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black">
          <Card className="max-h-[90vh] w-full max-w-2xl overflow-auto">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Info className="h-6 w-6" />
                  Event Details
                </CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedEvent(null)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-semibold text-gray-600">Event:</span>
                    <p>{selectedEvent.eventstr}</p>
                  </div>
                  <div>
                    <span className="font-semibold text-gray-600">
                      Timestamp:
                    </span>
                    <p>{new Date(selectedEvent.timestamp).toLocaleString()}</p>
                  </div>
                  <div>
                    <span className="font-semibold text-gray-600">
                      Machine:
                    </span>
                    <p>{device.name}</p>
                  </div>
                  <div>
                    <span className="font-semibold text-gray-600">
                      Machine ID:
                    </span>
                    <p>{selectedEvent.machineId}</p>
                  </div>
                </div>

                {selectedEvent.imagesFetched && (
                  <div className="space-y-4">
                    <h3 className="font-semibold">Event Images</h3>
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      {selectedEvent.croppedImageUrl && (
                        <div>
                          <p className="mb-2 text-sm font-medium text-gray-600">
                            Cropped Image
                          </p>
                          <Image
                            src={selectedEvent.croppedImageUrl}
                            alt="Cropped event image"
                            width={300}
                            height={200}
                            className="w-full rounded border object-contain"
                          />
                        </div>
                      )}
                      {selectedEvent.fullImageUrl && (
                        <div>
                          <p className="mb-2 text-sm font-medium text-gray-600">
                            Full Image
                          </p>
                          <Image
                            src={selectedEvent.fullImageUrl}
                            alt="Full event image"
                            width={300}
                            height={200}
                            className="w-full rounded border object-contain"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {selectedEvent.fetchingImages && (
                  <div className="flex items-center justify-center py-8">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-6 w-6 animate-spin" />
                      <span>Loading images...</span>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </section>
  );
}
