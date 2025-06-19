import React, { useCallback, useEffect, useState } from 'react';
import useOrganization from '@/hooks/use-organization';
import { usePubSub } from '@/hooks/use-pub-sub';
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
  images_requested?: boolean; // New field to track if images were requested
  event_severity?: string;
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
  images_requested?: boolean; // New field to track if images were requested
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
  is_critical: boolean;
}

// MQTT Event Message structure (similar to live-alert)
interface EventMessage {
  image_c_key: string;
  image_f_key: string;
  event_severity: string;
  meta: {
    node_id: string;
    hb_count: string;
    last_hb_time: string;
    photos_taken: string;
    events_seen: string;
  };
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
  const [historicalEvents, setHistoricalEvents] = useState<HistoricalEvent[]>([]);
  const [loadingHistorical, setLoadingHistorical] = useState(false);
  const [loadingImages, setLoadingImages] = useState<Record<string, boolean>>({});
  
  // New state for image loading pagination
  const [loadingMoreImages, setLoadingMoreImages] = useState(false);
  const [imagesLoadedCounter, setImagesLoadedCounter] = useState(0);
  const IMAGES_PER_BATCH = 10;

  console.log('imagesLoadedCounter', imagesLoadedCounter);

  // New state for MQTT live events
  const [liveEvents, setLiveEvents] = useState<MachineEvent[]>([]);
  const [mqttConnected, setMqttConnected] = useState(false);

  // Generate MQTT topics for the selected machine
  const mqttTopics = React.useMemo(() => {
    if (!selectedMachine || !organizationId) return [];

    const today = new Date().toISOString().split('T')[0]; // YYYY-mm-dd format
    return [
      `${organizationId}/_all_/${today}/${selectedMachine.id}/_all_/EVENT/#`,
    ];
  }, [organizationId, selectedMachine]);

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

  // Handle MQTT messages for live events
  const handleMqttMessage = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async (topic: string, data: any) => {
      try {
        if (!selectedMachine) return;

        // Parse the event message
        const eventMessage: EventMessage = data;

        // Create new live event
        const newEvent: MachineEvent = {
          id: `live-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
          eventstr: `Event detected - Severity ${eventMessage.event_severity}`,
          image_c_key: eventMessage.image_c_key,
          image_f_key: eventMessage.image_f_key,
          images_loaded: false,
          images_requested: false,
          event_severity: eventMessage.event_severity,
        };

        // FIX: Prepend the new event to the liveEvents array instead of overwriting it
        setLiveEvents((prev) => [newEvent, ...prev]);

        // Start fetching images for this event automatically (live events should load immediately)
        if (eventMessage.image_c_key && eventMessage.image_f_key) {
          setLoadingImages((prev) => ({ ...prev, [newEvent.id]: true })); // Use functional update for setLoadingImages

          try {
            const imageUrls = await fetchEventImages({
              image_c_key: eventMessage.image_c_key,
              image_f_key: eventMessage.image_f_key,
            });

            if (imageUrls) {
              setLiveEvents((prev) =>
                prev.map((event) =>
                  event.id === newEvent.id
                    ? {
                        ...event,
                        cropped_image_url: imageUrls.croppedImageUrl,
                        full_image_url: imageUrls.fullImageUrl,
                        images_loaded: true,
                        images_requested: true,
                      }
                    : event,
                ),
              );
            }
          } catch (error) {
            console.warn(
              `Failed to fetch images for event ${newEvent.id}:`,
              error,
            );
            // Mark as loaded even if failed so loading indicator disappears
            setLiveEvents((prev) =>
              prev.map((event) =>
                event.id === newEvent.id
                  ? { ...event, images_loaded: true, images_requested: true }
                  : event,
              ),
            );
          } finally {
            setLoadingImages((prev) => ({ ...prev, [newEvent.id]: false })); // Use functional update for setLoadingImages
          }
        }
      } catch (error) {
        console.error(
          'Error handling MQTT message in MachineDetailModal:',
          error,
        );
      }
    },
    [selectedMachine, fetchEventImages], // Added fetchEventImages to dependency array for completeness
  );

  // Use PubSub hook for MQTT connection
  const { isConnected, error } = usePubSub(mqttTopics, handleMqttMessage);

  // Update connection status
  useEffect(() => {
    setMqttConnected(isConnected);
  }, [isConnected]);



  // Function to fetch historical events for the past 7 days (metadata only)
  const fetchHistoricalEvents = useCallback(
    async (machineId: number) => {
      if (!token || !organizationId) return;

      setLoadingHistorical(true);
      setHistoricalEvents([]);
      setImagesLoadedCounter(0); // Reset counter
      setLiveEvents([]); // Clear live events when fetching historical for a new machine

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
                  images_requested: false, // Initialize as not requested
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

        // Show events immediately with metadata only
        setHistoricalEvents(allEvents);
        setLoadingHistorical(false);

        // DO NOT automatically fetch images - wait for user request
      } catch (error) {
        console.error('Error fetching historical events:', error);
        setLoadingHistorical(false);
      }
    },
    [token, organizationId],
  );

  // New function to load more images in batches
  const loadMoreImages = useCallback(async () => {
    if (loadingMoreImages) return;

    setLoadingMoreImages(true);

    try {
      // Get events that have image keys but haven't been requested yet
      const eventsNeedingImages = historicalEvents
        .filter(
          (event) => 
            event.image_c_key && 
            event.image_f_key && 
            !event.images_requested
        )
        .slice(0, IMAGES_PER_BATCH);

      if (eventsNeedingImages.length === 0) {
        setLoadingMoreImages(false);
        return;
      }

      // Mark these events as requested and set loading state
      setHistoricalEvents((prev) =>
        prev.map((event) => {
          if (eventsNeedingImages.some(e => e.id === event.id)) {
            setLoadingImages((loadingPrev) => ({ ...loadingPrev, [event.id]: true }));
            return { ...event, images_requested: true };
          }
          return event;
        })
      );

      // Fetch images for these events concurrently
      const imagePromises = eventsNeedingImages.map(async (event) => {
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
          } else {
            // Mark as loaded even if failed
            setHistoricalEvents((prev) =>
              prev.map((e) =>
                e.id === event.id ? { ...e, images_loaded: true } : e,
              ),
            );
          }
        } catch (error) {
          console.warn(
            `Failed to fetch images for event ${event.id}:`,
            error,
          );
          // Mark as loaded even if failed
          setHistoricalEvents((prev) =>
            prev.map((e) =>
              e.id === event.id ? { ...e, images_loaded: true } : e,
            ),
          );
        } finally {
          setLoadingImages((prev) => ({ ...prev, [event.id]: false }));
        }
      });

      await Promise.all(imagePromises);
      setImagesLoadedCounter(prev => prev + eventsNeedingImages.length);
    } catch (error) {
      console.error('Error loading more images:', error);
    } finally {
      setLoadingMoreImages(false);
    }
  }, [historicalEvents, loadingMoreImages, fetchEventImages]);

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
      setLiveEvents([]); // Ensure live events are also cleared
      setImagesLoadedCounter(0);
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

  // Calculate stats for load more button
  const eventsWithImages = historicalEvents.filter(
    (event) => event.image_c_key && event.image_f_key
  );
  const eventsWithImagesRequested = historicalEvents.filter(
    (event) => event.images_requested
  );
  const hasMoreImagesToLoad = eventsWithImagesRequested.length < eventsWithImages.length;

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

              {liveEvents.length > 0 && (
                <Badge
                  variant="outline"
                  className="border-orange-300 text-orange-700"
                >
                  {liveEvents.length} Live Event
                  {liveEvents.length > 1 ? 's' : ''}
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
                    MQTT Status:
                  </span>
                  <div className="text-sm">
                    <Badge variant={mqttConnected ? 'default' : 'destructive'}>
                      {mqttConnected ? 'Connected' : 'Disconnected'}
                    </Badge>
                  </div>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">
                    Location:
                  </span>
                  <div className="text-sm">
                    {selectedMachine?.last_location?.lat.toFixed(6) ?? '0.000000'},{' '}
                    {selectedMachine?.last_location?.long.toFixed(6) ?? '0.000000'}
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
                {liveEvents.length > 0 && liveEvents[0] && (
                  <div className="col-span-full">
                    <span className="text-sm font-medium text-gray-500">
                      Last Event:
                    </span>
                    <div className="text-sm">
                      {liveEvents[0].eventstr} -{' '}
                      {getTimeElapsed(liveEvents[0].timestamp)}
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
                  Live Events
                </TabsTrigger>
                <TabsTrigger
                  value="historical"
                  className="flex items-center gap-2"
                >
                  <ImageIcon className="h-4 w-4" />
                  Historical Events (7 days)
                  {historicalEvents.length > 0 && (
                    <Badge variant="outline" className="ml-1">
                      {historicalEvents.length}
                    </Badge>
                  )}
                </TabsTrigger>
              </TabsList>

              {/* Live Events Tab (MQTT) */}
              <TabsContent value="recent" className="mt-4">
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold">Live Events</h3>
                    <Badge
                      variant={mqttConnected ? 'default' : 'destructive'}
                      className="text-xs"
                    >
                      {mqttConnected ? 'Live' : 'Disconnected'}
                    </Badge>
                    {liveEvents.length > 0 && (
                      <Badge variant="outline">
                        {liveEvents.length} event
                        {liveEvents.length > 1 ? 's' : ''}
                      </Badge>
                    )}
                  </div>

                  {/* MQTT Connection Error */}
                  {error && (
                    <div className="rounded-lg border-l-4 border-l-red-500 bg-red-50/30 p-3">
                      <div className="text-sm text-red-700">
                        MQTT Connection Error: {error.message}
                      </div>
                    </div>
                  )}

                  {liveEvents.length === 0 ? (
                    <div className="py-12 text-center">
                      <Camera className="mx-auto mb-4 h-16 w-16 text-gray-300" />
                      <h3 className="mb-2 text-lg font-medium text-gray-600">
                        No Live Events
                      </h3>
                      <p className="text-gray-500">
                        {mqttConnected
                          ? 'Waiting for live events from this machine...'
                          : 'Connecting to MQTT to receive live events...'}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {liveEvents
                        .sort(
                          (a, b) =>
                            new Date(b.timestamp).getTime() -
                            new Date(a.timestamp).getTime(),
                        )
                        .map((event) => (
                          <Card
                            key={event.id}
                            className="border-l-4 border-l-green-500 bg-green-50/30"
                          >
                            <CardContent className="space-y-3 p-4">
                              <div className="flex items-start justify-between">
                                <div className="flex items-center gap-3">
                                  <Badge
                                    variant="default"
                                    className="bg-green-600"
                                  >
                                    Live Event
                                  </Badge>
                                  <div className="text-sm">
                                    <span className="font-medium">
                                      {event.eventstr}
                                    </span>
                                    {event.event_severity && (
                                      <Badge variant="outline" className="ml-2">
                                        Severity {event.event_severity}
                                      </Badge>
                                    )}
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

              {/* Historical Events Tab - Updated with lazy loading */}
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
                      {eventsWithImages.length > 0 && (
                        <Badge variant="secondary">
                          {eventsWithImagesRequested.length}/{eventsWithImages.length} images loaded
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

                                      {/* Updated Image Display Logic */}
                                      {event.image_c_key && event.image_f_key ? (
                                        // Event has image keys
                                        !event.images_requested ? (
                                          // Images not requested yet - show metadata only
                                          <div className="flex items-center justify-center rounded border bg-blue-50 py-8 text-blue-600">
                                            <div className="text-center">
                                              <ImageIcon className="mx-auto mb-2 h-8 w-8" />
                                              <p className="text-xs font-medium">
                                                Images Available
                                              </p>
                                              <p className="text-xs text-blue-500">
                                                {event.image_c_key ? 'Cropped' : ''}
                                                {event.image_c_key && event.image_f_key ? ' • ' : ''}
                                                {event.image_f_key ? 'Full' : ''}
                                              </p>
                                            </div>
                                          </div>
                                        ) : loadingImages[event.id] ? (
                                          // Images requested and loading
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
                                          // Images loaded successfully
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
                                        ) : (
                                          // Images requested but failed to load
                                          <div className="flex items-center justify-center rounded border bg-red-50 py-8 text-red-400">
                                            <div className="text-center">
                                              <ImageIcon className="mx-auto mb-2 h-8 w-8" />
                                              <p className="text-xs">
                                                Failed to load images
                                              </p>
                                            </div>
                                          </div>
                                        )
                                      ) : (
                                        // No image keys available
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
                      
                      {/* Load More Images Button */}
                      {hasMoreImagesToLoad && (
                        <div className="flex justify-center pt-6">
                          <Button
                            onClick={loadMoreImages}
                            disabled={loadingMoreImages}
                            variant="outline"
                            size="lg"
                            className="flex items-center gap-2"
                          >
                            {loadingMoreImages ? (
                              <>
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Loading Images...
                              </>
                            ) : (
                              <>
                                <ImageIcon className="h-4 w-4" />
                                Load More Images ({Math.min(IMAGES_PER_BATCH, eventsWithImages.length - eventsWithImagesRequested.length)})
                              </>
                            )}
                          </Button>
                        </div>
                      )}
                      
                      {!hasMoreImagesToLoad && eventsWithImages.length > 0 && (
                        <div className="text-center pt-4">
                          <p className="text-sm text-gray-500">
                            All images have been loaded ({eventsWithImages.length} total)
                          </p>
                        </div>
                      )}
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