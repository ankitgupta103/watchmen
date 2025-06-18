import React, { useCallback, useEffect, useState } from 'react';
import useOrganization from '@/hooks/use-organization';
import useToken from '@/hooks/use-token';
import {
  Calendar,
  Camera,
  Clock,
  Image as ImageIcon,
  Loader2,
  MapPin,
  X,
} from 'lucide-react';
import Image from 'next/image';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { Machine } from '@/lib/types/machine';
import { formatBufferSize, toTitleCase } from '@/lib/utils';

interface MachineEvent {
  id: string;
  timestamp: Date;
  eventstr: string;
  image_c_key?: string;
  image_f_key?: string;
  cropped_image_url?: string;
  full_image_url?: string;
  images_loaded?: boolean;
}

interface HistoricalEvent {
  id: string;
  timestamp: Date | string;
  eventstr: string;
  image_c_key?: string;
  image_f_key?: string;
  cropped_image_url?: string;
  full_image_url?: string;
  images_loaded?: boolean;
  date: string; // Date string for grouping
}

interface SimpleMachineData {
  machine_id: number;
  events: MachineEvent[];
  event_count: number;
  last_event?: MachineEvent;
  last_updated: string;
  // Status and location from useMachineStats
  is_online: boolean;
  location: { lat: number; lng: number };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  stats_data: any;
  buffer_size: number;
  // Add pulsating state for recent events
  is_pulsating: boolean;
}

interface MachineDetailModalProps {
  selectedMachine: Machine | null;
  setSelectedMachine: React.Dispatch<React.SetStateAction<Machine | null>>;
  getMachineData: (machineId: number) => SimpleMachineData;
}

export default function MachineDetailModal({
  selectedMachine,
  setSelectedMachine,
  getMachineData,
}: MachineDetailModalProps) {
  const { token } = useToken();
  const { organizationId } = useOrganization();
  const [selectedImageUrl, setSelectedImageUrl] = useState<string | null>(null);
  const [historicalEvents, setHistoricalEvents] = useState<HistoricalEvent[]>(
    [],
  );
  const [loadingHistorical, setLoadingHistorical] = useState(false);
  const [loadingImages, setLoadingImages] = useState<Record<string, boolean>>(
    {},
  );

  // Function to fetch images for events
  const fetchEventImages = useCallback(
    async (imageKeys: { image_c_key: string; image_f_key: string }) => {
      try {
        if (!token) return null;

        const data = await fetcherClient<{
          success: boolean;
          cropped_image_url?: string;
          full_image_url?: string;
          error?: string;
        }>(`${API_BASE_URL}/event-images/`, token, {
          method: 'POST',
          body: {
            image_c_key: imageKeys.image_c_key,
            image_f_key: imageKeys.image_f_key,
          },
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

  // Function to fetch historical events for the past 7 days
  const fetchHistoricalEvents = useCallback(
    async (machineId: number) => {
      if (!token || !organizationId) return;

      setLoadingHistorical(true);
      setHistoricalEvents([]);

      try {
        const allEvents: HistoricalEvent[] = [];
        const today = new Date();

        // Fetch events for the past 7 days
        for (let i = 0; i < 7; i++) {
          const date = new Date(today);
          date.setDate(date.getDate() - i);
          const dateStr = date.toLocaleDateString('en-CA'); // YYYY-MM-DD format

          try {
            const result = await fetcherClient<{
              success: boolean;
              events?: Array<{
                image_c_key: string;
                image_f_key: string;
                eventstr: string;
                timestamp?: string | Date;
              }>;
              error?: string;
            }>(`${API_BASE_URL}/s3-events/fetch-events/`, token, {
              method: 'POST',
              body: {
                org_id: organizationId,
                date: dateStr,
                machine_id: machineId,
              },
            });

            if (result?.success && result.events) {
              const dayEvents: HistoricalEvent[] = result.events.map(
                (event, index) => ({
                  id: `historical-${machineId}-${dateStr}-${index}`,
                  timestamp: event.timestamp
                    ? new Date(event.timestamp)
                    : new Date(dateStr + 'T12:00:00'),
                  eventstr: event.eventstr,
                  image_c_key: event.image_c_key,
                  image_f_key: event.image_f_key,
                  images_loaded: false,
                  date: dateStr,
                }),
              );

              allEvents.push(...dayEvents);
            }
          } catch (err) {
            console.warn(`Failed to fetch events for ${dateStr}:`, err);
          }
        }

        // Sort events by timestamp (most recent first)
        allEvents.sort(
          (a, b) =>
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
        );

        // Show events immediately without waiting for images
        setHistoricalEvents(allEvents);
        setLoadingHistorical(false);

        // Start fetching images concurrently for all events that have image keys
        const eventsWithImages = allEvents.filter(
          (event) => event.image_c_key && event.image_f_key,
        );

        // Fetch images concurrently (not sequentially) for better performance
        eventsWithImages.forEach(async (event) => {
          setLoadingImages((prev) => ({ ...prev, [event.id]: true }));

          try {
            const imageUrls = await fetchEventImages({
              image_c_key: event.image_c_key!,
              image_f_key: event.image_f_key!,
            });

            if (imageUrls) {
              setHistoricalEvents((prev) =>
                prev.map((e) =>
                  e.id === event.id
                    ? {
                        ...e,
                        cropped_image_url: imageUrls.croppedImageUrl,
                        full_image_url: imageUrls.fullImageUrl,
                        images_loaded: true,
                      }
                    : e,
                ),
              );
            }
          } catch (error) {
            console.warn(
              `Failed to fetch images for event ${event.id}:`,
              error,
            );
            // Mark as loaded even if failed so loading indicator disappears
            setHistoricalEvents((prev) =>
              prev.map((e) =>
                e.id === event.id ? { ...e, images_loaded: true } : e,
              ),
            );
          } finally {
            setLoadingImages((prev) => ({ ...prev, [event.id]: false }));
          }
        });
      } catch (error) {
        console.error('Error fetching historical events:', error);
        setLoadingHistorical(false);
      }
    },
    [token, organizationId, fetchEventImages],
  );

  // Fetch historical events when machine is selected
  useEffect(() => {
    if (selectedMachine) {
      fetchHistoricalEvents(selectedMachine.id);
    }
  }, [selectedMachine, fetchHistoricalEvents]);

  // Reset state when modal closes
  useEffect(() => {
    if (!selectedMachine) {
      setHistoricalEvents([]);
      setLoadingImages({});
      setSelectedImageUrl(null);
    }
  }, [selectedMachine]);

  if (!selectedMachine) return null;

  const machineData = getMachineData(selectedMachine.id);

  // Format time elapsed
  const getTimeElapsed = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);

    if (minutes > 0) {
      return `${minutes}m ${seconds}s ago`;
    }
    return `${seconds}s ago`;
  };

  // Group historical events by date
  const groupedHistoricalEvents = historicalEvents.reduce(
    (acc, event) => {
      const date = event.date;
      if (!acc[date]) {
        acc[date] = [];
      }
      acc[date].push(event);
      return acc;
    },
    {} as Record<string, HistoricalEvent[]>,
  );

  return (
    <>
      <Dialog
        open={!!selectedMachine}
        onOpenChange={() => setSelectedMachine(null)}
      >
        <DialogContent className="flex h-full max-h-[90vh] w-full max-w-6xl flex-col overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-xl">
              <Camera className="h-6 w-6 text-blue-600" />
              {toTitleCase(selectedMachine.name)}

              {machineData.event_count > 0 && (
                <Badge
                  variant="outline"
                  className="border-orange-300 text-orange-700"
                >
                  {machineData.event_count} Recent Event
                  {machineData.event_count > 1 ? 's' : ''}
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-6">
            {/* Machine Info Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <MapPin className="h-5 w-5" />
                  Machine Information
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Machine ID:
                  </span>
                  <div className="text-sm">{selectedMachine.id}</div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Machine UID:
                  </span>
                  <div className="text-sm">{selectedMachine.machine_uid}</div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Type:
                  </span>
                  <div className="text-sm capitalize">
                    {selectedMachine.type.replace('_', ' ')}
                  </div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Status:
                  </span>
                  <div className="text-sm">
                    <Badge
                      variant={
                        machineData.is_online ? 'default' : 'destructive'
                      }
                    >
                      {machineData.is_online ? 'Online' : 'Offline'}
                    </Badge>
                  </div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Location:
                  </span>
                  <div className="text-sm">
                    {machineData.location.lat.toFixed(6)},{' '}
                    {machineData.location.lng.toFixed(6)}
                  </div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Owner:
                  </span>
                  <div className="text-sm">
                    {selectedMachine.current_owner_name}
                  </div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Buffer Size:
                  </span>
                  <div className="text-sm">
                    {formatBufferSize(machineData.buffer_size)}
                  </div>
                </div>
                {machineData.last_event && (
                  <div className="col-span-full">
                    <span className="text-sm font-medium text-gray-500">
                      Last Event:
                    </span>
                    <div className="text-sm">
                      {machineData.last_event.eventstr} -{' '}
                      {getTimeElapsed(machineData.last_event.timestamp)}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Separator />

            {/* Tabbed Events and Images Section */}
            <Tabs defaultValue="recent" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="recent" className="flex items-center gap-2">
                  <Camera className="h-4 w-4" />
                  Recent Events
                  {machineData.event_count > 0 && (
                    <Badge variant="outline" className="ml-1">
                      {machineData.event_count}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger
                  value="historical"
                  className="flex items-center gap-2"
                >
                  <ImageIcon className="h-4 w-4" />
                  Images Captured (7 days)
                  {historicalEvents.length > 0 && (
                    <Badge variant="outline" className="ml-1">
                      {historicalEvents.length}
                    </Badge>
                  )}
                </TabsTrigger>
              </TabsList>

              {/* Recent Events Tab */}
              <TabsContent value="recent" className="mt-4">
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold">Live Events</h3>
                    {machineData.event_count > 0 && (
                      <Badge variant="outline">
                        {machineData.event_count} event
                        {machineData.event_count > 1 ? 's' : ''}
                      </Badge>
                    )}
                  </div>

                  {machineData.events.length === 0 ? (
                    <div className="py-12 text-center">
                      <Camera className="mx-auto mb-4 h-16 w-16 text-gray-300" />
                      <h3 className="mb-2 text-lg font-medium text-gray-600">
                        No Recent Events
                      </h3>
                      <p className="text-gray-500">
                        This machine hasn&apos;t triggered any events recently
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {machineData.events
                        .sort(
                          (a, b) =>
                            new Date(b.timestamp).getTime() -
                            new Date(a.timestamp).getTime(),
                        )
                        .map((event) => (
                          <Card
                            key={event.id}
                            className="border-l-4 border-l-orange-500 bg-orange-50/30"
                          >
                            <CardContent className="space-y-3 p-4">
                              <div className="flex items-start justify-between">
                                <div className="flex items-center gap-3">
                                  <Badge variant="secondary">Live Event</Badge>
                                  <div className="text-sm">
                                    <span className="font-medium">
                                      {event.eventstr}
                                    </span>
                                  </div>
                                </div>
                                <div className="flex items-center gap-1">
                                  <Clock className="h-3 w-3 text-gray-400" />
                                  <span className="text-xs text-gray-500">
                                    {getTimeElapsed(event.timestamp)}
                                  </span>
                                </div>
                              </div>

                              {/* Image Display */}
                              {event.images_loaded &&
                              (event.cropped_image_url ||
                                event.full_image_url) ? (
                                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                                  {event.cropped_image_url && (
                                    <div className="space-y-2">
                                      <div className="text-sm font-medium text-gray-700">
                                        Cropped Image:
                                      </div>
                                      <Image
                                        src={event.cropped_image_url}
                                        alt={`Cropped image for event ${event.eventstr}`}
                                        width={200}
                                        height={150}
                                        className="cursor-pointer rounded-lg border shadow-sm transition-transform hover:scale-105"
                                        onClick={() =>
                                          setSelectedImageUrl(
                                            event.cropped_image_url!,
                                          )
                                        }
                                      />
                                    </div>
                                  )}
                                  {event.full_image_url && (
                                    <div className="space-y-2">
                                      <div className="text-sm font-medium text-gray-700">
                                        Full Image:
                                      </div>
                                      <Image
                                        src={event.full_image_url}
                                        alt={`Full image for event ${event.eventstr}`}
                                        width={200}
                                        height={150}
                                        className="cursor-pointer rounded-lg border shadow-sm transition-transform hover:scale-105"
                                        onClick={() =>
                                          setSelectedImageUrl(
                                            event.full_image_url!,
                                          )
                                        }
                                      />
                                    </div>
                                  )}
                                </div>
                              ) : !event.images_loaded &&
                                (event.image_c_key || event.image_f_key) ? (
                                <div className="flex items-center gap-2 text-sm text-gray-500">
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                  Loading images...
                                </div>
                              ) : (
                                <div className="text-sm text-gray-500">
                                  No images available for this event
                                </div>
                              )}

                              <div className="text-xs text-gray-500">
                                <Calendar className="mr-1 inline h-3 w-3" />
                                {new Date(event.timestamp).toLocaleString()}
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* Historical Images Tab */}
              <TabsContent value="historical" className="mt-4">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold">
                        Historical Events
                      </h3>
                      {historicalEvents.length > 0 && (
                        <Badge variant="outline">
                          {historicalEvents.length} events (7 days)
                        </Badge>
                      )}
                    </div>
                    {loadingHistorical && (
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading historical events...
                      </div>
                    )}
                  </div>

                  {loadingHistorical ? (
                    <div className="py-12 text-center">
                      <Loader2 className="mx-auto mb-4 h-16 w-16 animate-spin text-gray-300" />
                      <h3 className="mb-2 text-lg font-medium text-gray-600">
                        Loading Historical Events
                      </h3>
                      <p className="text-gray-500">
                        Fetching events from the past 7 days...
                      </p>
                    </div>
                  ) : Object.keys(groupedHistoricalEvents).length === 0 ? (
                    <div className="py-12 text-center">
                      <ImageIcon className="mx-auto mb-4 h-16 w-16 text-gray-300" />
                      <h3 className="mb-2 text-lg font-medium text-gray-600">
                        No Historical Events
                      </h3>
                      <p className="text-gray-500">
                        No events found for this machine in the past 7 days
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {Object.entries(groupedHistoricalEvents)
                        .sort(([a], [b]) => b.localeCompare(a)) // Sort dates in descending order
                        .map(([date, events]) => (
                          <div key={date} className="space-y-3">
                            <div className="flex items-center gap-2 border-b pb-2">
                              <Calendar className="h-4 w-4 text-gray-500" />
                              <h4 className="text-sm font-semibold text-gray-700">
                                {new Date(date).toLocaleDateString('en-US', {
                                  weekday: 'long',
                                  year: 'numeric',
                                  month: 'long',
                                  day: 'numeric',
                                })}
                              </h4>
                              <Badge variant="outline" className="text-xs">
                                {events.length} events
                              </Badge>
                            </div>

                            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                              {events.map((event) => (
                                <Card
                                  key={event.id}
                                  className="border bg-gray-50/50"
                                >
                                  <CardContent className="p-3">
                                    <div className="space-y-2">
                                      <div className="flex items-center justify-between">
                                        <Badge
                                          variant="outline"
                                          className="text-xs"
                                        >
                                          {event.eventstr}
                                        </Badge>
                                        <span className="text-xs text-gray-500">
                                          {new Date(
                                            event.timestamp,
                                          ).toLocaleTimeString()}
                                        </span>
                                      </div>

                                      {/* Image Display */}
                                      {event.image_c_key &&
                                      event.image_f_key ? (
                                        loadingImages[event.id] ? (
                                          <div className="flex items-center justify-center rounded border bg-gray-50 py-8">
                                            <div className="text-center">
                                              <Loader2 className="mx-auto mb-2 h-6 w-6 animate-spin text-gray-400" />
                                              <p className="text-xs text-gray-500">
                                                Loading images...
                                              </p>
                                            </div>
                                          </div>
                                        ) : event.images_loaded &&
                                          (event.cropped_image_url ||
                                            event.full_image_url) ? (
                                          <div className="space-y-2">
                                            {event.cropped_image_url && (
                                              <div>
                                                <p className="mb-1 text-xs text-gray-500">
                                                  Cropped
                                                </p>
                                                <Image
                                                  src={event.cropped_image_url}
                                                  alt={`Historical event ${event.eventstr}`}
                                                  width={150}
                                                  height={100}
                                                  className="h-24 w-full cursor-pointer rounded border object-cover transition-transform hover:scale-105"
                                                  onClick={() =>
                                                    setSelectedImageUrl(
                                                      event.cropped_image_url!,
                                                    )
                                                  }
                                                />
                                              </div>
                                            )}
                                            {event.full_image_url && (
                                              <div>
                                                <p className="mb-1 text-xs text-gray-500">
                                                  Full
                                                </p>
                                                <Image
                                                  src={event.full_image_url}
                                                  alt={`Historical event ${event.eventstr}`}
                                                  width={150}
                                                  height={100}
                                                  className="h-24 w-full cursor-pointer rounded border object-cover transition-transform hover:scale-105"
                                                  onClick={() =>
                                                    setSelectedImageUrl(
                                                      event.full_image_url!,
                                                    )
                                                  }
                                                />
                                              </div>
                                            )}
                                          </div>
                                        ) : event.images_loaded ? (
                                          <div className="flex items-center justify-center rounded border bg-gray-50 py-8 text-gray-400">
                                            <div className="text-center">
                                              <ImageIcon className="mx-auto mb-2 h-8 w-8" />
                                              <p className="text-xs">
                                                Images not available
                                              </p>
                                            </div>
                                          </div>
                                        ) : (
                                          <div className="flex animate-pulse items-center justify-center rounded border bg-gray-100 py-8">
                                            <div className="text-center">
                                              <div className="mx-auto mb-2 h-8 w-8 rounded bg-gray-300"></div>
                                              <p className="text-xs text-gray-500">
                                                Preparing to load...
                                              </p>
                                            </div>
                                          </div>
                                        )
                                      ) : (
                                        <div className="flex items-center justify-center rounded border bg-gray-50 py-8 text-gray-400">
                                          <div className="text-center">
                                            <ImageIcon className="mx-auto mb-2 h-8 w-8" />
                                            <p className="text-xs">
                                              No images for this event
                                            </p>
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  </CardContent>
                                </Card>
                              ))}
                            </div>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </DialogContent>
      </Dialog>

      {/* Image Viewer Modal */}
      {selectedImageUrl && (
        <Dialog
          open={!!selectedImageUrl}
          onOpenChange={() => setSelectedImageUrl(null)}
        >
          <DialogHeader className="pb-2">
            <DialogTitle className="flex items-center justify-between">
              Event Image
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedImageUrl(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>
          <DialogContent className="flex max-h-[90vh] max-w-4xl flex-col items-center justify-center p-2">
            <div className="flex h-full w-full items-center justify-center">
              <Image
                src={selectedImageUrl}
                alt="Event image full view"
                width={1000}
                height={1000}
                className="h-full max-h-[75vh] w-auto rounded-lg bg-white object-contain shadow-lg"
                style={{ background: 'white' }}
              />
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
