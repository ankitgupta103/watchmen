'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import useOrganization from '@/hooks/use-organization';
import useToken from '@/hooks/use-token';
import { Filter, X } from 'lucide-react';
import { DateRange } from 'react-day-picker';

import DateRangePicker from '@/components/common/date-range-picker';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { FeedEvent, S3EventFeedResponse } from '@/lib/types/activity';
import { Machine, MachineTag } from '@/lib/types/machine';
import { getSeverityLabel } from '@/lib/utils/severity';

import Event from './event';

const severityLevels = [
  { id: 0, label: 'LOW', description: 'No person detected' },
  { id: 1, label: 'MEDIUM', description: 'Person detected' },
  { id: 2, label: 'HIGH', description: 'Person with suspicious item' },
  { id: 3, label: 'CRITICAL', description: 'Weapon detected' },
];

export default function EventsFeed({
  machines,
  allTags,
}: {
  machines: Machine[];
  allTags: MachineTag[];
}) {
  const { token } = useToken();
  const { organizationId } = useOrganization();

  const [s3FeedEvents, setS3FeedEvents] = useState<S3EventFeedResponse>();
  const [chunk, setChunk] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [search, setSearch] = useState<string>('');
  const [selectedTags, setSelectedTags] = useState<number[]>([]);
  const [selectedSeverities, setSelectedSeverities] = useState<number[]>([]);
  const [dateRange, setDateRange] = useState<DateRange>({
    from: new Date(new Date().setDate(new Date().getDate() - 30)),
    to: new Date(),
  });

  const fetchEvents = useCallback(
    async (currentChunk: number) => {
      if (
        !token ||
        !organizationId ||
        !machines ||
        !dateRange.from ||
        !dateRange.to
      ) {
        return;
      }
      setIsLoading(true);

      const payload = {
        org_id: organizationId.toString(),
        end_date: dateRange.to.toISOString().split('T')[0],
        start_date: dateRange.from.toISOString().split('T')[0],
        machine_ids: machines.map((machine) => machine.id),
        tag_ids: selectedTags,
        severity_levels: selectedSeverities,
        chunk: currentChunk,
      };

      try {
        const response = await fetcherClient<S3EventFeedResponse>(
          `${API_BASE_URL}/s3-events/fetch-events/`,
          token,
          {
            method: 'PUT',
            body: payload,
          },
        );

        if (response && response.success) {
          if (currentChunk === 1) {
            setS3FeedEvents(response);
          } else {
            setS3FeedEvents((prev) => ({
              ...response,
              events: [...(prev?.events || []), ...response.events],
            }));
          }
          setChunk(currentChunk);
        }
      } catch (error) {
        console.error('Failed to fetch events:', error);
      } finally {
        setIsLoading(false);
      }
    },
    [
      token,
      organizationId,
      machines,
      dateRange,
      selectedTags,
      selectedSeverities,
    ],
  );

  useEffect(() => {
    fetchEvents(1);
  }, [dateRange, selectedTags, selectedSeverities, fetchEvents]);

  useEffect(() => {
    // Create a sentinel element to observe
    const sentinel = document.createElement('div');
    sentinel.style.height = '1px';
    sentinel.style.position = 'absolute';
    sentinel.style.bottom = '200px';
    sentinel.style.width = '100%';

    const container = document.body;
    container.appendChild(sentinel);

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && !isLoading && s3FeedEvents?.has_next) {
          fetchEvents(chunk + 1);
        }
      },
      {
        threshold: 0.1,
        rootMargin: '200px',
      },
    );

    observer.observe(sentinel);

    return () => {
      observer.disconnect();
      if (container.contains(sentinel)) {
        container.removeChild(sentinel);
      }
    };
  }, [isLoading, s3FeedEvents, chunk, fetchEvents]);

  const filteredEvents = useMemo(() => {
    if (!s3FeedEvents?.events) return [];
    if (!search) return s3FeedEvents.events;

    return s3FeedEvents.events.filter((event) => {
      const lowerCaseSearch = search.toLowerCase();
      return (
        event.machine_id.toString().toLowerCase().includes(lowerCaseSearch) ||
        machines
          .find((machine) => machine.id === event.machine_id)
          ?.name.toLowerCase()
          .includes(lowerCaseSearch) ||
        getSeverityLabel(event.severity)
          .label.toLowerCase()
          .includes(lowerCaseSearch) ||
        event.cropped_images.some((croppedImage) =>
          croppedImage.class_name.toLowerCase().includes(lowerCaseSearch),
        )
      );
    });
  }, [s3FeedEvents?.events, search, machines]);

  const handleStartDateChange = useCallback((date: Date) => {
    setDateRange((prev) => ({ ...prev, from: date }));
  }, []);

  const handleEndDateChange = useCallback((date: Date) => {
    setDateRange((prev) => ({ ...prev, to: date }));
  }, []);

  const handleLoadMore = () => {
    if (!isLoading && s3FeedEvents?.has_next) {
      fetchEvents(chunk + 1);
    }
  };

  const handleTagToggle = useCallback((tagId: number) => {
    console.log('Toggling tag:', tagId);
    setSelectedTags((prev) => {
      const newTags = prev.includes(tagId)
        ? prev.filter((id) => id !== tagId)
        : [...prev, tagId];
      console.log('New selected tags:', newTags);
      return newTags;
    });
    // Reset chunk when tags change to start from beginning
    setChunk(1);
    // Clear existing events to prevent showing stale data
    setS3FeedEvents(() => undefined);
  }, []);

  const handleSeverityToggle = useCallback((severityId: number) => {
    console.log('Toggling severity:', severityId);
    setSelectedSeverities((prev) => {
      const newSeverities = prev.includes(severityId)
        ? prev.filter((id) => id !== severityId)
        : [...prev, severityId];
      console.log('New selected severities:', newSeverities);
      return newSeverities;
    });
    // Reset chunk when severities change to start from beginning
    setChunk(1);
    // Clear existing events to prevent showing stale data
    setS3FeedEvents(() => undefined);
  }, []);

  const clearTagFilters = useCallback(() => {
    console.log('Clearing all tag filters');
    setSelectedTags([]);
    // Reset chunk when clearing tags to start from beginning
    setChunk(1);
    // Clear existing events to prevent showing stale data
    setS3FeedEvents(undefined);
  }, []);

  const clearSeverityFilters = useCallback(() => {
    console.log('Clearing all severity filters');
    setSelectedSeverities([]);
    // Reset chunk when clearing severities to start from beginning
    setChunk(1);
    // Clear existing events to prevent showing stale data
    setS3FeedEvents(undefined);
  }, []);

  const clearAllFilters = useCallback(() => {
    console.log('Clearing all filters');
    setSelectedTags([]);
    setSelectedSeverities([]);
    // Reset chunk when clearing all filters to start from beginning
    setChunk(1);
    // Clear existing events to prevent showing stale data
    setS3FeedEvents(undefined);
  }, []);

  // Fixed: Create a proper mapping between tag IDs and names
  const getSelectedTagsWithNames = useMemo(() => {
    return selectedTags
      .map((tagId) => {
        const tag = allTags.find((tag) => tag.id === tagId);
        return tag ? { id: tagId, name: tag.name } : null;
      })
      .filter((tag): tag is { id: number; name: string } => tag !== null);
  }, [selectedTags, allTags]);

  // Create a mapping for selected severities with labels
  const getSelectedSeveritiesWithLabels = useMemo(() => {
    return selectedSeverities
      .map((severityId) => {
        const severity = severityLevels.find((s) => s.id === severityId);
        return severity ? { id: severityId, label: severity.label } : null;
      })
      .filter(
        (severity): severity is { id: number; label: string } =>
          severity !== null,
      );
  }, [selectedSeverities]);

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center gap-2">
        <Input
          className="h-10 flex-1"
          placeholder="Filter by Machine ID, Severity, Detected Object..."
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="h-10 px-3">
              <Filter className="mr-2 h-4 w-4" />
              Tags
              {selectedTags.length > 0 && (
                <span className="ml-2 rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-800">
                  {selectedTags.length}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end">
            <DropdownMenuLabel>Filter by Tags</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {allTags.map((tag) => (
              <DropdownMenuCheckboxItem
                key={tag.id}
                checked={selectedTags.includes(tag.id)}
                onCheckedChange={() => handleTagToggle(tag.id)}
              >
                {tag.name}
              </DropdownMenuCheckboxItem>
            ))}
            {selectedTags.length > 0 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuCheckboxItem
                  onCheckedChange={clearTagFilters}
                  className="text-red-600 focus:text-red-600"
                >
                  <X className="mr-2 h-4 w-4" />
                  Clear All
                </DropdownMenuCheckboxItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="h-10 px-3">
              <Filter className="mr-2 h-4 w-4" />
              Severity
              {selectedSeverities.length > 0 && (
                <span className="ml-2 rounded-full bg-orange-100 px-2 py-1 text-xs text-orange-800">
                  {selectedSeverities.length}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end">
            <DropdownMenuLabel>Filter by Severity</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {severityLevels.map((severity) => (
              <DropdownMenuCheckboxItem
                key={severity.id}
                checked={selectedSeverities.includes(severity.id)}
                onCheckedChange={() => handleSeverityToggle(severity.id)}
              >
                <div>
                  <div className="font-medium">{severity.label}</div>
                  <div className="text-muted-foreground text-xs">
                    {severity.description}
                  </div>
                </div>
              </DropdownMenuCheckboxItem>
            ))}
            {selectedSeverities.length > 0 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuCheckboxItem
                  onCheckedChange={clearSeverityFilters}
                  className="text-red-600 focus:text-red-600"
                >
                  <X className="mr-2 h-4 w-4" />
                  Clear All
                </DropdownMenuCheckboxItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <DateRangePicker
          setSelectStartDate={handleStartDateChange}
          setSelectEndDate={handleEndDateChange}
        />
      </div>

      {(selectedTags.length > 0 || selectedSeverities.length > 0) && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-muted-foreground text-sm">Active filters:</span>

          {/* Tag filters */}
          {getSelectedTagsWithNames.map((tag) => (
            <span
              key={`tag-${tag.id}`}
              className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-800"
            >
              Tag: {tag.name}
              <button
                onClick={() => handleTagToggle(tag.id)}
                className="ml-1 rounded-full p-0.5 hover:bg-blue-200"
                aria-label={`Remove ${tag.name} filter`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}

          {/* Severity filters */}
          {getSelectedSeveritiesWithLabels.map((severity) => (
            <span
              key={`severity-${severity.id}`}
              className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2 py-1 text-xs text-orange-800"
            >
              Severity: {severity.label}
              <button
                onClick={() => handleSeverityToggle(severity.id)}
                className="ml-1 rounded-full p-0.5 hover:bg-orange-200"
                aria-label={`Remove ${severity.label} severity filter`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}

          <Button
            variant="ghost"
            size="sm"
            onClick={clearAllFilters}
            className="h-6 px-2 text-xs"
          >
            Clear All
          </Button>
        </div>
      )}

      <div className="space-y-4">
        {filteredEvents.length > 0
          ? filteredEvents.map((event: FeedEvent) => (
              <Event
                key={`${event.annotated_image_path}-${event.timestamp}`}
                event={event}
                machines={machines}
              />
            ))
          : !isLoading && (
              <div className="text-muted-foreground text-center text-sm">
                No events found
              </div>
            )}
      </div>

      {s3FeedEvents?.has_next && !isLoading && (
        <div className="mt-4 text-center">
          <Button
            onClick={handleLoadMore}
            className="rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
          >
            Load More Events
          </Button>
        </div>
      )}

      {isLoading && (
        <div className="text-muted-foreground text-center text-sm">
          Loading...
        </div>
      )}
    </div>
  );
}
