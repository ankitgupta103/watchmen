'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Image from 'next/image';
import { Camera, Clock, AlertTriangle, Loader2, Calendar } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar as CalendarComponent } from '@/components/ui/calendar';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { Machine, S3EventsResponse, FeedEvent } from '@/lib/types/machine';
import { getPresignedUrl } from '@/lib/utils/presigned-url';
import { cn } from '@/lib/utils';

import useToken from '@/hooks/use-token';

interface EventsFeedProps {
  machines: Machine[];
  orgId: number;
}

interface DateRange {
  startDate: Date;
  endDate: Date;
}

// Fallback date formatting function
const formatTimeAgo = (date: Date): string => {
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  return `${Math.floor(diffInSeconds / 86400)}d ago`;
};

// Format date to YYYY-MM-DD
const formatDateForAPI = (date: Date): string => {
  return date.toISOString().split('T')[0];
};

// Get default date range (1 month ago to today)
const getDefaultDateRange = (): DateRange => {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setMonth(startDate.getMonth() - 1);
  return { startDate, endDate };
};

// Get preset date ranges
const getPresetDateRange = (preset: string): DateRange => {
  const endDate = new Date();
  const startDate = new Date();
  
  switch (preset) {
    case '7days':
      startDate.setDate(startDate.getDate() - 7);
      break;
    case '1month':
      startDate.setMonth(startDate.getMonth() - 1);
      break;
    case '3months':
      startDate.setMonth(startDate.getMonth() - 3);
      break;
    default:
      return getDefaultDateRange();
  }
  
  return { startDate, endDate };
};

export default function EventsFeed({ machines, orgId }: EventsFeedProps) {
  const { token } = useToken();
  const [events, setEvents] = useState<FeedEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingImages, setLoadingImages] = useState<Record<string, boolean>>({});
  const [currentChunk, setCurrentChunk] = useState(1);
  const [hasNext, setHasNext] = useState(true);
  const [totalEvents, setTotalEvents] = useState(0);
  const [totalChunks, setTotalChunks] = useState(0);
  
  // Date filtering state
  const [dateRange, setDateRange] = useState<DateRange>(getDefaultDateRange());
  const [selectedPreset, setSelectedPreset] = useState<string>('1month');
  const [showCustomDatePicker, setShowCustomDatePicker] = useState(false);

  const loadingRef = useRef(loading);
  loadingRef.current = loading;

  const observerRef = useRef<IntersectionObserver | null>(null);
  const lastEventRef = useRef<HTMLDivElement | null>(null);

  // Sort events by timestamp (newest first)
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }, [events]);

  const fetchEvents = useCallback(async (chunk: number, append: boolean = false) => {
    if (!token || loadingRef.current) return;

    setLoading(true);
    try {
      const machineIds = machines.filter(m => m.id).map(m => m.id);
      
      // If no machines are available, don't make the API call
      if (machineIds.length === 0) {
        console.warn('No machines available, skipping events fetch');
        setLoading(false);
        return;
      }
      
      const requestBody = {
        org_id: orgId.toString(),
        chunk,
        machine_ids: machineIds,
        start_date: formatDateForAPI(dateRange.startDate),
        end_date: formatDateForAPI(dateRange.endDate),
      };
      
      const response = await fetcherClient<S3EventsResponse>(
        `${API_BASE_URL}/s3-events/fetch-events/`,
        token,
        {
          method: 'PUT',
          body: requestBody,
        }
      );

      if (response?.success) {
        const newEvents: FeedEvent[] = response.events.map((event, index) => {
          // Try to find machine info from the event data or fallback to first machine
          const machineId = event.machine_id || machines[0]?.id || 0;
          const machine = machines.find(m => m.id === machineId) || machines[0];
          
          return {
            ...event,
            id: `${event.timestamp || Date.now()}-${index}`,
            machineId: machineId,
            machineName: machine?.name || 'Unknown Machine',
            machineType: machine?.type || 'Unknown Type',
            timestamp: event.timestamp ? new Date(event.timestamp) : new Date(),
            imagesLoaded: false,
            severity: event.event_severity || '0',
          };
        });

        if (append) {
          setEvents(prev => [...prev, ...newEvents]);
        } else {
          setEvents(newEvents);
        }

        setCurrentChunk(response.chunk);
        setHasNext(response.has_next);
        setTotalEvents(response.total_events);
        setTotalChunks(response.total_chunks);
      }
    } catch (error) {
      console.error('Failed to fetch events:', error);
    } finally {
      setLoading(false);
    }
  }, [token, orgId, machines, dateRange]);

  const fetchImagesForEvent = useCallback(async (event: FeedEvent) => {
    if (!token || event.imagesLoaded) return;

    setLoadingImages(prev => ({ ...prev, [event.id]: true }));
    
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

      setEvents(prev => 
        prev.map(e => 
          e.id === event.id 
            ? { 
                ...e, 
                croppedImageUrl: croppedImageUrl || undefined,
                fullImageUrl: fullImageUrl || undefined,
                imagesLoaded: true 
              }
            : e
        )
      );
    } catch (error) {
      console.error('Failed to fetch images for event:', event.id, error);
      // Mark as loaded even if failed to prevent infinite retries
      setEvents(prev => 
        prev.map(e => 
          e.id === event.id ? { ...e, imagesLoaded: true } : e
        )
      );
    } finally {
      setLoadingImages(prev => ({ ...prev, [event.id]: false }));
    }
  }, [token]);

  const loadMoreEvents = useCallback(() => {
    if (hasNext && !loading) {
      fetchEvents(currentChunk + 1, true);
    }
  }, [hasNext, loading, currentChunk, fetchEvents]);

  // Handle preset date range changes
  const handlePresetChange = useCallback((preset: string) => {
    setSelectedPreset(preset);
    if (preset === 'custom') {
      setShowCustomDatePicker(true);
    } else {
      const newDateRange = getPresetDateRange(preset);
      setDateRange(newDateRange);
      setShowCustomDatePicker(false);
      // Reset events and fetch with new date range
      setEvents([]);
      setCurrentChunk(1);
      setHasNext(true);
      // Trigger fetch with new date range
      setTimeout(() => {
        if (machines.length > 0) {
          fetchEvents(1);
        }
      }, 100);
    }
  }, [machines, fetchEvents]);

  // Handle custom date selection
  const handleCustomDateSelect = useCallback((start: Date | undefined, end: Date | undefined) => {
    if (start && end) {
      const newDateRange = { startDate: start, endDate: end };
      setDateRange(newDateRange);
      setShowCustomDatePicker(false);
      // Reset events and fetch with new date range
      setEvents([]);
      setCurrentChunk(1);
      setHasNext(true);
      // Trigger fetch with new date range
      setTimeout(() => {
        if (machines.length > 0) {
          fetchEvents(1);
        }
      }, 100);
    }
  }, [machines, fetchEvents]);

  // Intersection observer for infinite scroll
  const lastEventCallback = useCallback((node: HTMLDivElement | null) => {
    if (observerRef.current) observerRef.current.disconnect();
    
    if (node) {
      observerRef.current = new IntersectionObserver(entries => {
        if (entries[0].isIntersecting && hasNext && !loading) {
          loadMoreEvents();
        }
      });
      observerRef.current.observe(node);
    }
    lastEventRef.current = node;
  }, [hasNext, loading, loadMoreEvents]);

  // Initial fetch
  useEffect(() => {
    fetchEvents(1);
  }, [fetchEvents]);

  // Fetch images for visible events
  useEffect(() => {
    const visibleEvents = sortedEvents.slice(0, 20); // Load images for first 20 events
    visibleEvents.forEach(event => {
      if (!event.imagesLoaded) {
        fetchImagesForEvent(event);
      }
    });
  }, [sortedEvents, fetchImagesForEvent]);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case '1': return 'bg-yellow-500 text-black';
      case '2': return 'bg-orange-500 text-white';
      case '3': return 'bg-red-500 text-white';
      default: return 'bg-gray-500 text-white';
    }
  };

  const getSeverityText = (severity: string) => {
    switch (severity) {
      case '1': return 'Low';
      case '2': return 'High';
      case '3': return 'Critical';
      default: return 'Unknown';
    }
  };

  if (events.length === 0 && loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading events...</span>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4 p-4">
      {/* Header with date filter */}
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Events Feed</h2>
        <p className="text-gray-600 mb-4">
          {totalEvents} total events • {totalChunks} chunks
        </p>
        
        {/* Date Range Selector */}
        <div className="flex items-center justify-center gap-3">
          <Select value={selectedPreset} onValueChange={handlePresetChange}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Select time range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7days">Last 7 days</SelectItem>
              <SelectItem value="1month">Last month</SelectItem>
              <SelectItem value="3months">Last 3 months</SelectItem>
              <SelectItem value="custom">Custom dates</SelectItem>
            </SelectContent>
          </Select>

          {selectedPreset === 'custom' && (
            <Popover open={showCustomDatePicker} onOpenChange={setShowCustomDatePicker}>
              <PopoverTrigger asChild>
                <Button variant="outline" className="w-40">
                  <Calendar className="mr-2 h-4 w-4" />
                  Custom dates
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="center">
                <CalendarComponent
                  mode="range"
                  selected={{
                    from: dateRange.startDate,
                    to: dateRange.endDate,
                  }}
                  onSelect={(range) => handleCustomDateSelect(range?.from, range?.to)}
                  numberOfMonths={2}
                  disabled={(date) => date > new Date()}
                />
              </PopoverContent>
            </Popover>
          )}

          <div className="text-sm text-gray-500">
            {formatDateForAPI(dateRange.startDate)} to {formatDateForAPI(dateRange.endDate)}
          </div>
        </div>
      </div>

      {sortedEvents.map((event, index) => (
        <Card key={event.id} className="overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <Camera className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">{event.machineName}</h3>
                  <p className="text-sm text-gray-500 capitalize">
                    {event.machineType.replace(/_/g, ' ')}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <Badge className={cn('text-xs', getSeverityColor(event.severity))}>
                  {getSeverityText(event.severity)}
                </Badge>
                <div className="flex items-center text-xs text-gray-500">
                  <Clock className="h-3 w-3 mr-1" />
                  {formatTimeAgo(event.timestamp)}
                </div>
              </div>
            </div>
          </CardHeader>

          <CardContent className="pt-0">
            {event.eventstr && (
              <p className="text-gray-700 mb-4">{event.eventstr}</p>
            )}

            <div className="grid grid-cols-2 gap-3 mb-4">
              {event.croppedImageUrl && (
                <div className="relative">
                  <Image
                    src={event.croppedImageUrl}
                    alt="Cropped image"
                    width={200}
                    height={200}
                    className="w-full h-32 object-cover rounded-lg"
                  />
                  <Badge variant="secondary" className="absolute top-2 left-2 text-xs">
                    Cropped
                  </Badge>
                </div>
              )}
              
              {event.fullImageUrl && (
                <div className="relative">
                  <Image
                    src={event.fullImageUrl}
                    alt="Full image"
                    width={200}
                    height={200}
                    className="w-full h-32 object-cover rounded-lg"
                  />
                  <Badge variant="secondary" className="absolute top-2 left-2 text-xs">
                    Full
                  </Badge>
                </div>
              )}

              {loadingImages[event.id] && (
                <div className="col-span-2 flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                  <span className="ml-2 text-sm text-gray-500">Loading images...</span>
                </div>
              )}
            </div>

            {event.cropped_images && event.cropped_images.length > 0 && (
              <div className="border-t pt-3">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Detected Objects:</h4>
                <div className="flex flex-wrap gap-2">
                  {event.cropped_images.map((crop, idx) => (
                    <Badge key={idx} variant="outline" className="text-xs">
                      {crop.class_name} ({Math.round(crop.confidence * 100)}%)
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Intersection observer target for infinite scroll */}
            {index === sortedEvents.length - 1 && (
              <div ref={lastEventCallback} className="h-4" />
            )}
          </CardContent>
        </Card>
      ))}

      {loading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span className="ml-2">Loading more events...</span>
        </div>
      )}

      {!hasNext && events.length > 0 && (
        <div className="text-center py-8 text-gray-500">
          <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>No more events to load</p>
        </div>
      )}

      {events.length === 0 && !loading && (
        <div className="text-center py-20 text-gray-500">
          <Camera className="h-16 w-16 mx-auto mb-4 opacity-30" />
          <h3 className="text-lg font-medium mb-2">No events found</h3>
          <p>No events found for the selected date range</p>
        </div>
      )}
    </div>
  );
}
