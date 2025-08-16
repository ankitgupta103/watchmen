'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Image from 'next/image';
import { Camera, Clock, AlertTriangle, Loader2, Calendar, Filter, TrendingUp, Search } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar as CalendarComponent } from '@/components/ui/calendar';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { Machine, S3EventsResponse, FeedEvent, MachineTag } from '@/lib/types/machine';
import { getPresignedUrl } from '@/lib/utils/presigned-url';
import { calculateSeverity, getSeverityLabel, getSeverityColor } from '@/lib/utils/severity';
import { cn } from '@/lib/utils';

import useToken from '@/hooks/use-token';
import ImageModal from './image-modal';
import TagFilter from './tag-filter';
import TagDisplay from '../../devices/components/tag-display';

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

// Get preset date range
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

export default function EventsFeed({ machines, orgId }: EventsFeedProps) {
  const { token } = useToken();
  const [events, setEvents] = useState<FeedEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingImages, setLoadingImages] = useState<Record<string, boolean>>({});
  const [currentChunk, setCurrentChunk] = useState(1);
  const [hasNext, setHasNext] = useState(true);
  
  // Date filtering state
  const [dateRange, setDateRange] = useState<DateRange>(getDefaultDateRange());
  const [selectedPreset, setSelectedPreset] = useState<string>('1month');
  const [tempDateRange, setTempDateRange] = useState<DateRange | null>(null);
  
  // Tag filtering state
  const [selectedTags, setSelectedTags] = useState<MachineTag[]>([]);
  
  // Search and filter state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedMachine, setSelectedMachine] = useState<string>('all');

  // Image modal state
  const [modalImage, setModalImage] = useState<{
    url: string;
    alt: string;
    title: string;
  } | null>(null);

  const observerRef = useRef<IntersectionObserver | null>(null);
  const processedEventsRef = useRef<Set<string>>(new Set());
  const isInitialLoad = useRef(true);

  // Sort events by timestamp (newest first) and filter by all criteria
  const sortedEvents = useMemo(() => {
    let filteredEvents = [...events];
    
    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filteredEvents = filteredEvents.filter(event => 
        event.machineName.toLowerCase().includes(query) ||
        event.eventstr?.toLowerCase().includes(query) ||
        event.cropped_images?.some(img => 
          img.class_name.toLowerCase().includes(query)
        )
      );
    }
    
    // Filter by severity
    if (selectedSeverity !== 'all') {
      const severityLevel = parseInt(selectedSeverity);
      filteredEvents = filteredEvents.filter(event => event.severity === severityLevel);
    }
    
    // Filter by machine
    if (selectedMachine !== 'all') {
      const machineId = parseInt(selectedMachine);
      filteredEvents = filteredEvents.filter(event => event.machineId === machineId);
    }
    
    // Filter by selected tags if any are selected
    if (selectedTags.length > 0) {
      filteredEvents = filteredEvents.filter(event => {
        const machine = machines.find(m => m.id === event.machineId);
        if (!machine?.tags || machine.tags.length === 0) return false;
        
        // Check if the machine has any of the selected tags
        return selectedTags.some(selectedTag => 
          machine.tags?.some(machineTag => machineTag.id === selectedTag.id)
        );
      });
    }
    
    return filteredEvents.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }, [events, searchQuery, selectedSeverity, selectedMachine, selectedTags, machines]);

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
          const severity = calculateSeverity(event.cropped_images);
          
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
    
    const newDateRange = getPresetDateRange(preset);
    setDateRange(newDateRange);
    
    // Reset and fetch new events
    setEvents([]);
    setCurrentChunk(1);
    setHasNext(true);
    processedEventsRef.current.clear();
  }, []);

  // Handle custom date selection (temporary)
  const handleCustomDateSelect = useCallback((range: { from?: Date; to?: Date } | undefined) => {
    if (range?.from) {
      setTempDateRange({
        startDate: range.from,
        endDate: range.to || range.from
      });
    }
  }, []);

  // Apply custom date range
  const applyCustomDateRange = useCallback(() => {
    if (tempDateRange) {
      setDateRange(tempDateRange);
      setSelectedPreset('custom');
      setTempDateRange(null);
      
      // Reset and fetch new events
      setEvents([]);
      setCurrentChunk(1);
      setHasNext(true);
      processedEventsRef.current.clear();
    }
  }, [tempDateRange]);

  // Clear custom date selection
  const clearCustomDateRange = useCallback(() => {
    setTempDateRange(null);
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

  // Clear all filters
  const clearAllFilters = useCallback(() => {
    setSearchQuery('');
    setSelectedSeverity('all');
    setSelectedMachine('all');
    setSelectedTags([]);
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
      <div className="max-w-6xl mx-auto space-y-6 p-4">
        {/* Header with search and filters */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-6 text-center">Events Feed</h2>
          
          {/* Search and Filters Row */}
          <div className="flex items-center justify-between gap-6 mb-6 flex-wrap">
            {/* Left side - Search */}
            <div className="flex-1 max-w-md">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Search events, machines, or objects..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            {/* Right side - Filters */}
            <div className="flex items-center gap-3 flex-wrap">
              {/* Criticality Filter */}
              <Select value={selectedSeverity} onValueChange={setSelectedSeverity}>
                <SelectTrigger className="w-44">
                  <SelectValue placeholder="All Criticality" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Criticality</SelectItem>
                  <SelectItem value="0">No Person</SelectItem>
                  <SelectItem value="1">Person Detected</SelectItem>
                  <SelectItem value="2">Person + Item</SelectItem>
                  <SelectItem value="3">Weapon Detected</SelectItem>
                </SelectContent>
              </Select>

              {/* Machine Filter */}
              <Select value={selectedMachine} onValueChange={setSelectedMachine}>
                <SelectTrigger className="w-44">
                  <SelectValue placeholder="All Machines" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Machines</SelectItem>
                  {machines.map((machine) => (
                    <SelectItem key={machine.id} value={machine.id.toString()}>
                      {machine.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

            <TagFilter selectedTags={selectedTags} onTagsChange={setSelectedTags} />

              {/* Date Range Filter */}
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="w-48 justify-start">
                    <Calendar className="mr-2 h-4 w-4" />
                    <span className="truncate">
                      {selectedPreset === 'custom' 
                        ? `${formatDateForAPI(dateRange.startDate)} - ${formatDateForAPI(dateRange.endDate)}`
                        : selectedPreset === '7days' ? 'Last 7 days'
                        : selectedPreset === '1month' ? 'Last 30 days'
                        : 'Last 90 days'
                      }
                    </span>
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="end">
                  <div className="p-4">
                    <div className="space-y-4">
                      <div>
                        <h4 className="font-medium text-sm mb-3">Quick filters</h4>
                        <div className="grid grid-cols-1 gap-2">
                          <Button
                            variant={selectedPreset === '7days' ? 'default' : 'ghost'}
                            className="justify-start h-8"
                            onClick={() => handlePresetChange('7days')}
                          >
                            Last 7 days
                          </Button>
                          <Button
                            variant={selectedPreset === '1month' ? 'default' : 'ghost'}
                            className="justify-start h-8"
                            onClick={() => handlePresetChange('1month')}
                          >
                            Last 30 days
                          </Button>
                          <Button
                            variant={selectedPreset === '3months' ? 'default' : 'ghost'}
                            className="justify-start h-8"
                            onClick={() => handlePresetChange('3months')}
                          >
                            Last 90 days
                          </Button>
                        </div>
                      </div>
                      
                      <div className="border-t pt-4">
                        <h4 className="font-medium text-sm mb-3">Custom range</h4>
                        <CalendarComponent
                          mode="range"
                          selected={{
                            from: tempDateRange?.startDate,
                            to: tempDateRange?.endDate,
                          }}
                          onSelect={handleCustomDateSelect}
                          numberOfMonths={2}
                          className="rounded-md"
                        />
                        
                        {tempDateRange && (
                          <div className="mt-4 pt-4 border-t flex items-center justify-between">
                            <div className="text-sm text-gray-600">
                              {formatDateForAPI(tempDateRange.startDate)} - {formatDateForAPI(tempDateRange.endDate)}
                            </div>
                            <div className="flex gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setTempDateRange(null)}
                              >
                                Cancel
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={clearCustomDateRange}
                              >
                                Clear
                              </Button>
                              <Button
                                size="sm"
                                onClick={applyCustomDateRange}
                              >
                                Apply
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          </div>
        </div>

        {/* Results Summary */}
        {(searchQuery || selectedSeverity !== 'all' || selectedMachine !== 'all' || selectedTags.length > 0) && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-medium text-blue-900">
                  Showing {sortedEvents.length} events
                  {searchQuery && ` matching "${searchQuery}"`}
                  {selectedSeverity !== 'all' && ` with ${
                    selectedSeverity === '0' ? 'No Person' :
                    selectedSeverity === '1' ? 'Person Detected' :
                    selectedSeverity === '2' ? 'Person + Item' :
                    'Weapon Detected'
                  } criticality`}
                  {selectedMachine !== 'all' && ` from ${machines.find(m => m.id.toString() === selectedMachine)?.name || 'selected machine'}`}
                  {selectedTags.length > 0 && ` with selected tags`}
                </span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAllFilters}
                className="text-blue-600 hover:text-blue-700"
              >
                Clear All Filters
              </Button>
            </div>
          </div>
        )}

        {/* No Results Message */}
        {sortedEvents.length === 0 && (searchQuery || selectedSeverity !== 'all' || selectedMachine !== 'all' || selectedTags.length > 0) && (
          <div className="text-center py-12">
            <Filter className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No events found</h3>
            <p className="text-gray-500 mb-4">No events found matching the current filters.</p>
            <Button
              variant="outline"
              onClick={clearAllFilters}
            >
              Clear All Filters
            </Button>
          </div>
        )}

        {/* Events List */}
        {sortedEvents.map((event, index) => {
          const severityInfo = getSeverityLabel(event.severity);
          return (
            <Card key={event.id} className="overflow-hidden border-l-4" style={{ borderLeftColor: getSeverityColor(event.severity).split(' ')[0].replace('bg-', '') }}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                      <Camera className="h-6 w-6 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 text-lg">{event.machineName}</h3>
                      <p className="text-sm text-gray-500 capitalize">
                        {event.machineType.replace(/_/g, ' ')}
                      </p>
                      {/* Machine Tags */}
                      <div className="mt-2">
                        <TagDisplay 
                          tags={machines.find(m => m.id === event.machineId)?.tags || []} 
                          showDeleteButtons={false}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Badge className={cn('text-sm px-3 py-1', getSeverityColor(event.severity))}>
                          <span className="mr-1">{severityInfo.icon}</span>
                          {severityInfo.label}
                        </Badge>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="font-medium">{severityInfo.description}</p>
                      </TooltipContent>
                    </Tooltip>
                    <div className="flex items-center text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                      <Clock className="h-4 w-4 mr-2" />
                      {formatTimeAgo(event.timestamp)}
                    </div>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="pt-0">
                {event.eventstr && (
                  <p className="text-gray-700 mb-4 bg-gray-50 p-3 rounded-lg">{event.eventstr}</p>
                )}

                <div className="space-y-4 mb-4 grid grid-cols-5 gap-4">
                  {/* Full Image */}
                  {event.fullImageUrl && (
                    <div className="relative col-span-3">
                      <Image
                        src={event.fullImageUrl}
                        alt="Full image"
                        width={400}
                        height={300}
                        className="w-full h-full object-cover rounded-lg cursor-pointer hover:opacity-90 transition-opacity border"
                        onClick={() => handleImageClick(event.fullImageUrl!, 'Full image', 'Full Image')}
                      />
                      <Badge variant="secondary" className="absolute top-2 left-2 text-xs">
                        Full Image
                      </Badge>
                    </div>
                  )}
                  
                  {/* Cropped Images */}
                  {event.croppedImageUrls && event.croppedImageUrls.length > 0 && (
                    <div className="col-span-2">
                      <h4 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                        <Filter className="h-4 w-4 mr-2" />
                        Detected Objects ({event.croppedImageUrls.length})
                      </h4>
                      <div className="grid grid-cols-2 gap-2">
                        {event.croppedImageUrls.map((url, idx) => {
                          const croppedImage = event.cropped_images?.[idx];
                          const className = croppedImage?.class_name || 'Unknown';
                          const confidence = croppedImage?.confidence || 0;
                          
                          return (
                            <Tooltip key={idx}>
                              <TooltipTrigger asChild>
                                <div className="relative group">
                                  <Image
                                    src={url}
                                    alt={`Detected ${className}`}
                                    width={100}
                                    height={100}
                                    className="w-24 h-full object-cover rounded-lg cursor-pointer hover:opacity-90 transition-opacity border group-hover:shadow-md"
                                    onClick={() => handleImageClick(
                                      url,
                                      `Detected ${className}`,
                                      `${className} (${Math.round(confidence * 100)}%)`
                                    )}
                                  />
                                  <Badge variant="secondary" className="absolute top-1 left-1 text-xs">
                                    {idx + 1}
                                  </Badge>
                                  <div className="absolute bottom-1 right-1 bg-black bg-opacity-70 text-white text-xs px-1 py-0.5 rounded">
                                    {Math.round(confidence * 100)}%
                                  </div>
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
                  <div className="border-t pt-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                      <TrendingUp className="h-4 w-4 mr-2" />
                      Detection Details
                    </h4>
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
          );
        })}

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