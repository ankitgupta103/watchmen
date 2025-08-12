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
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { Machine, S3EventsResponse, FeedEvent, CroppedImage } from '@/lib/types/machine';
import { getPresignedUrl } from '@/lib/utils/presigned-url';
import { cn } from '@/lib/utils';

import useToken from '@/hooks/use-token';
import ImageModal from './image-modal';

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

// Determine event severity based on detected objects
const determineEventSeverity = (croppedImages: CroppedImage[]): string => {
  if (!croppedImages || croppedImages.length === 0) return '0';
  
  const detectedClasses = croppedImages.map(img => img.class_name.toLowerCase());
  
  // Check for gun first (highest priority)
  if (detectedClasses.some(cls => cls.includes('gun') || cls.includes('weapon') || cls.includes('firearm'))) {
    return '3'; // Critical
  }
  
  // Check for person + backpack combination
  const hasPerson = detectedClasses.some(cls => cls.includes('person') || cls.includes('human'));
  const hasBackpack = detectedClasses.some(cls => cls.includes('backpack') || cls.includes('bag'));
  
  if (hasPerson && hasBackpack) {
    return '2'; // High
  }
  
  // Check for person only
  if (hasPerson) {
    return '1'; // Low
  }
  
  return '0'; // Unknown/No person detected
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

  // Image modal state
  const [modalImage, setModalImage] = useState<{
    url: string;
    alt: string;
    title: string;
  } | null>(null);

  const loadingRef = useRef(loading);
  loadingRef.current = loading;

  const observerRef = useRef<IntersectionObserver | null>(null);
  const lastEventRef = useRef<HTMLDivElement | null>(null);
  
  // Ref to track which events have been processed for image loading
  const processedEventsRef = useRef<Set<string>>(new Set());

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
          
          // Determine severity based on detected objects in cropped images
          const severity = determineEventSeverity(event.cropped_images);
          
          return {
            ...event,
            id: `${event.timestamp || Date.now()}-${index}`,
            machineId: machineId,
            machineName: machine?.name || 'Unknown Machine',
            machineType: machine?.type || 'Unknown Type',
            timestamp: event.timestamp ? new Date(Number(event.timestamp) * 1000) : new Date(),
            imagesLoaded: false,
            severity: severity,
          };
        });

        if (append) {
          setEvents(prev => [...prev, ...newEvents]);
        } else {
          setEvents(newEvents);
          // Reset processed events tracking when fetching new events
          processedEventsRef.current.clear();
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
    if (!token || event.imagesLoaded || processedEventsRef.current.has(event.id)) return;

    // Mark this event as being processed
    processedEventsRef.current.add(event.id);
    setLoadingImages(prev => ({ ...prev, [event.id]: true }));
    
    try {
      let fullImageUrl: string | null = null;
      const croppedImageUrls: string[] = [];

      // Get presigned URL for full image from original_image_path
      if (event.original_image_path) {
        fullImageUrl = await getPresignedUrl(event.original_image_path, token);
      }

      // Get presigned URLs for all cropped images
      if (event.cropped_images && event.cropped_images.length > 0) {
        const croppedUrlPromises = event.cropped_images.map(async (crop) => {
          if (crop.image_file_path) {
            const url = await getPresignedUrl(crop.image_file_path, token);
            return url;
          }
          return null;
        });
        
        const urls = await Promise.all(croppedUrlPromises);
        urls.forEach(url => {
          if (url) croppedImageUrls.push(url);
        });
      }

      setEvents(prev => 
        prev.map(e => 
          e.id === event.id 
            ? { 
                ...e, 
                fullImageUrl: fullImageUrl || undefined,
                croppedImageUrls: croppedImageUrls,
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
      // Clear processed events tracking
      processedEventsRef.current.clear();
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
      // Clear processed events tracking
      processedEventsRef.current.clear();
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

  // Handle image click to open modal
  const handleImageClick = useCallback((url: string, alt: string, title: string) => {
    setModalImage({ url, alt, title });
  }, []);

  // Close image modal
  const closeImageModal = useCallback(() => {
    setModalImage(null);
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchEvents(1);
  }, [fetchEvents]);

  // Fetch images for visible events
  useEffect(() => {
    const visibleEvents = sortedEvents.slice(0, 20); // Load images for first 20 events
    const unprocessedEvents = visibleEvents.filter(event => 
      !event.imagesLoaded && !processedEventsRef.current.has(event.id)
    );
    
    unprocessedEvents.forEach(event => {
      fetchImagesForEvent(event);
    });
  }, [sortedEvents.length, fetchImagesForEvent]); // Only depend on events count, not the events array itself

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case '1': return 'bg-blue-500 text-white'; // Person detected - blue
      case '2': return 'bg-orange-500 text-white'; // Person + backpack - orange
      case '3': return 'bg-red-600 text-white'; // Gun detected - red
      default: return 'bg-gray-400 text-white'; // No person - gray
    }
  };

  const getSeverityText = (severity: string) => {
    switch (severity) {
      case '1': return 'Person Detected';
      case '2': return 'Person + Backpack';
      case '3': return 'Gun Detected';
      default: return 'No Person';
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
    <>
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

              <div className="space-y-3 mb-4">
                {event.fullImageUrl && (
                  <div className="relative">
                    <Image
                      src={event.fullImageUrl}
                      alt="Full image"
                      width={400}
                      height={300}
                      className="w-full h-48 object-cover rounded-lg cursor-pointer hover:opacity-90 transition-opacity"
                      onClick={() => handleImageClick(
                        event.fullImageUrl!,
                        'Full image',
                        'Full Image'
                      )}
                    />
                    <Badge variant="secondary" className="absolute top-2 left-2 text-xs">
                      Full Image
                    </Badge>
                  </div>
                )}
                
                {event.croppedImageUrls && event.croppedImageUrls.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Detected Objects:</h4>
                    <div className="grid grid-cols-4 gap-2">
                      {event.croppedImageUrls.map((url, idx) => {
                        const croppedImage = event.cropped_images?.[idx];
                        const className = croppedImage?.class_name || 'Unknown';
                        const confidence = croppedImage?.confidence || 0;
                        
                        return (
                          <Tooltip key={idx}>
                            <TooltipTrigger asChild>
                              <div className="relative">
                                <Image
                                  src={url}
                                  alt={`Cropped image ${idx + 1}`}
                                  width={100}
                                  height={100}
                                  className="w-full h-20 object-cover rounded-lg cursor-pointer hover:opacity-90 transition-opacity"
                                  onClick={() => handleImageClick(
                                    url,
                                    `Cropped image ${idx + 1}`,
                                    `${className} (${Math.round(confidence * 100)}%)`
                                  )}
                                />
                                <Badge variant="secondary" className="absolute top-1 left-1 text-xs">
                                  {idx + 1}
                                </Badge>
                              </div>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p className="font-medium">{className}</p>
                              <p className="text-xs opacity-80">
                                Confidence: {Math.round(confidence * 100)}%
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        );
                      })}
                    </div>
                  </div>
                )}

                {loadingImages[event.id] && (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                    <span className="ml-2 text-sm text-gray-500">Loading images...</span>
                  </div>
                )}
              </div>

              {event.cropped_images && event.cropped_images.length > 0 && (
                <div className="border-t pt-3">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Detection Details:</h4>
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

      {/* Image Modal */}
      {modalImage && (
        <ImageModal
          isOpen={!!modalImage}
          onClose={closeImageModal}
          imageUrl={modalImage.url}
          imageAlt={modalImage.alt}
          title={modalImage.title}
        />
      )}
    </>
  );
}
