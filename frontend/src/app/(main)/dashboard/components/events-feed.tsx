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

// Format time ago
const formatTimeAgo = (date: Date): string => {
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  return `${Math.floor(diffInSeconds / 86400)}d ago`;
};

// Format date for API (YYYY-MM-DD in local timezone)
const formatDateForAPI = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// Get default date range (30 days ago to today)
const getDefaultDateRange = (): DateRange => {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - 30);
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
      startDate.setDate(startDate.getDate() - 30);
      break;
    case '3months':
      startDate.setDate(startDate.getDate() - 90);
      break;
    default:
      return getDefaultDateRange();
  }
  
  return { startDate, endDate };
};

// Determine event severity
const determineEventSeverity = (croppedImages: CroppedImage[]): string => {
  if (!croppedImages?.length) return '0';
  
  const detectedClasses = croppedImages.map(img => img.class_name.toLowerCase());
  
  // Check for weapons (highest priority)
  if (detectedClasses.some(cls => 
    cls.includes('gun') || cls.includes('weapon') || cls.includes('firearm') || cls.includes('knife')
  )) {
    return '3';
  }
  
  // Check for person + suspicious items
  const hasPerson = detectedClasses.some(cls => cls.includes('person') || cls.includes('human'));
  const hasSuspiciousItem = detectedClasses.some(cls => 
    cls.includes('backpack') || cls.includes('bag') || cls.includes('suitcase')
  );
  
  if (hasPerson && hasSuspiciousItem) return '2';
  if (hasPerson) return '1';
  
  return '0';
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

  const observerRef = useRef<IntersectionObserver | null>(null);
  const processedEventsRef = useRef<Set<string>>(new Set());
  const isInitialLoad = useRef(true);

  // Sort events by timestamp (newest first)
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }, [events]);

  const fetchEvents = useCallback(async (chunk: number, append: boolean = false) => {
    if (!token || loading || !machines.length) return;

    setLoading(true);
    try {
      const machineIds = machines.map(m => m.id).filter(Boolean);
      
      if (machineIds.length === 0) {
        console.warn('No valid machine IDs found');
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
      
      console.log('Fetching events with date range:', {
        start_date: formatDateForAPI(dateRange.startDate),
        end_date: formatDateForAPI(dateRange.endDate),
        chunk,
        machineIds
      });
      
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
          const machineId = event.machine_id || machines[0]?.id || 0;
          const machine = machines.find(m => m.id === machineId) || machines[0];
          const severity = determineEventSeverity(event.cropped_images);
          
          return {
            ...event,
            id: `${event.timestamp || Date.now()}-${machineId}-${index}`,
            machineId: machineId,
            machineName: machine?.name || 'Unknown Machine',
            machineType: machine?.type || 'Unknown Type',
            timestamp: new Date(Number(event.timestamp) * 1000), // Convert from seconds to milliseconds
            imagesLoaded: false,
            severity: severity,
          };
        });

        if (append) {
          setEvents(prev => [...prev, ...newEvents]);
        } else {
          setEvents(newEvents);
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
  }, [token, orgId, machines, dateRange, loading]);

  const fetchImagesForEvent = useCallback(async (event: FeedEvent) => {
    if (!token || event.imagesLoaded || processedEventsRef.current.has(event.id)) return;

    processedEventsRef.current.add(event.id);
    setLoadingImages(prev => ({ ...prev, [event.id]: true }));
    
    try {
      const [fullImageUrl, ...croppedImageUrls] = await Promise.all([
        // Get presigned URL for full image
        event.original_image_path ? getPresignedUrl(event.original_image_path, token) : Promise.resolve(null),
        // Get presigned URLs for cropped images
        ...(event.cropped_images?.map(crop => 
          crop.image_file_path ? getPresignedUrl(crop.image_file_path, token) : Promise.resolve(null)
        ) || [])
      ]);

      setEvents(prev => 
        prev.map(e => 
          e.id === event.id 
            ? { 
                ...e, 
                fullImageUrl: fullImageUrl || undefined,
                croppedImageUrls: croppedImageUrls.filter(Boolean) as string[],
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
      return;
    }

    const newDateRange = getPresetDateRange(preset);
    setDateRange(newDateRange);
    setShowCustomDatePicker(false);
    
    // Reset and fetch new events
    setEvents([]);
    setCurrentChunk(1);
    setHasNext(true);
    processedEventsRef.current.clear();
  }, []);

  // Handle custom date selection
  const handleCustomDateSelect = useCallback((start: Date | undefined, end: Date | undefined) => {
    if (start && end) {
      setDateRange({ startDate: start, endDate: end });
      setShowCustomDatePicker(false);
      
      // Reset and fetch new events
      setEvents([]);
      setCurrentChunk(1);
      setHasNext(true);
      processedEventsRef.current.clear();
    }
  }, []);

  // Intersection observer for infinite scroll
  const lastEventCallback = useCallback((node: HTMLDivElement | null) => {
    if (observerRef.current) observerRef.current.disconnect();
    
    if (node) {
      observerRef.current = new IntersectionObserver(entries => {
        if (entries[0].isIntersecting && hasNext && !loading) {
          loadMoreEvents();
        }
      }, {
        threshold: 0.1,
        rootMargin: '50px'
      });
      observerRef.current.observe(node);
    }
  }, [hasNext, loading, loadMoreEvents]);

  // Handle image modal
  const handleImageClick = useCallback((url: string, alt: string, title: string) => {
    setModalImage({ url, alt, title });
  }, []);

  const closeImageModal = useCallback(() => {
    setModalImage(null);
  }, []);

  // Initial fetch and refetch when date range changes
  useEffect(() => {
    if (machines.length > 0) {
      fetchEvents(1, false);
    }
  }, [dateRange]); // This will trigger when dateRange changes

  // Separate effect for initial load to avoid dependency issues
  useEffect(() => {
    if (isInitialLoad.current && machines.length > 0) {
      isInitialLoad.current = false;
      fetchEvents(1, false);
    }
  }, [machines.length]);

  // Load images for visible events
  useEffect(() => {
    const visibleEvents = sortedEvents.slice(0, Math.min(20, sortedEvents.length));
    visibleEvents
      .filter(event => !event.imagesLoaded && !processedEventsRef.current.has(event.id))
      .forEach(event => fetchImagesForEvent(event));
  }, [sortedEvents.length, fetchImagesForEvent]);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case '1': return 'bg-blue-500 text-white';
      case '2': return 'bg-orange-500 text-white';
      case '3': return 'bg-red-600 text-white';
      default: return 'bg-gray-400 text-white';
    }
  };

  const getSeverityText = (severity: string) => {
    switch (severity) {
      case '1': return 'Person Detected';
      case '2': return 'Person + Item';
      case '3': return 'Weapon Detected';
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
            {totalEvents} total events • Page {currentChunk} of {totalChunks}
          </p>
          
          {/* Date Range Selector */}
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <Select value={selectedPreset} onValueChange={handlePresetChange}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Select time range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7days">Last 7 days</SelectItem>
                <SelectItem value="1month">Last 30 days</SelectItem>
                <SelectItem value="3months">Last 90 days</SelectItem>
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

        {/* Events List */}
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
                {/* Full Image */}
                {event.fullImageUrl && (
                  <div className="relative">
                    <Image
                      src={event.fullImageUrl}
                      alt="Full image"
                      width={400}
                      height={300}
                      className="w-full h-48 object-cover rounded-lg cursor-pointer hover:opacity-90 transition-opacity"
                      onClick={() => handleImageClick(event.fullImageUrl!, 'Full image', 'Full Image')}
                    />
                    <Badge variant="secondary" className="absolute top-2 left-2 text-xs">
                      Full Image
                    </Badge>
                  </div>
                )}
                
                {/* Cropped Images */}
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
                                  alt={`Detected ${className}`}
                                  width={100}
                                  height={100}
                                  className="w-full h-20 object-cover rounded-lg cursor-pointer hover:opacity-90 transition-opacity"
                                  onClick={() => handleImageClick(
                                    url,
                                    `Detected ${className}`,
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

                {/* Loading indicator for images */}
                {loadingImages[event.id] && (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                    <span className="ml-2 text-sm text-gray-500">Loading images...</span>
                  </div>
                )}
              </div>

              {/* Detection Details */}
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

              {/* Intersection observer target */}
              {index === sortedEvents.length - 1 && (
                <div ref={lastEventCallback} className="h-4" />
              )}
            </CardContent>
          </Card>
        ))}

        {/* Loading more indicator */}
        {loading && events.length > 0 && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="ml-2">Loading more events...</span>
          </div>
        )}

        {/* No more events */}
        {!hasNext && events.length > 0 && (
          <div className="text-center py-8 text-gray-500">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No more events to load</p>
          </div>
        )}

        {/* No events found */}
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