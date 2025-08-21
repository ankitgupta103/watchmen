'use client';

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import useOrganization from '@/hooks/use-organization';
import useToken from '@/hooks/use-token';
import { DateRange } from 'react-day-picker';

import { Button } from '@/components/ui/button';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { FeedEvent, S3EventFeedResponse } from '@/lib/types/activity';
import { Machine, MachineTag } from '@/lib/types/machine';
import { getSeverityLabel } from '@/lib/utils/severity';

import Event from './event';
import FilterEvents from './filter-events';

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

  // Use refs to store the latest filter values to avoid stale closures
  const selectedTagsRef = useRef(selectedTags);
  const selectedSeveritiesRef = useRef(selectedSeverities);
  const dateRangeRef = useRef(dateRange);
  // Ref to hold the AbortController for the current fetch request
  const abortControllerRef = useRef<AbortController | null>(null);

  // Update refs whenever the values change
  useEffect(() => {
    selectedTagsRef.current = selectedTags;
  }, [selectedTags]);

  useEffect(() => {
    selectedSeveritiesRef.current = selectedSeverities;
  }, [selectedSeverities]);

  useEffect(() => {
    dateRangeRef.current = dateRange;
  }, [dateRange]);

  const fetchEvents = useCallback(
    async (currentChunk: number) => {
      // Cancel any ongoing fetch request before starting a new one
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create a new AbortController for the current request
      const controller = new AbortController();
      abortControllerRef.current = controller;

      if (
        !token ||
        !organizationId ||
        !machines ||
        !dateRangeRef.current.from ||
        !dateRangeRef.current.to
      ) {
        return;
      }
      setIsLoading(true);

      const payload = {
        org_id: organizationId.toString(),
        end_date: dateRangeRef.current.to.toISOString().split('T')[0],
        start_date: dateRangeRef.current.from.toISOString().split('T')[0],
        machine_ids: machines.map((machine) => machine.id),
        tag_ids: selectedTagsRef.current,
        severity_levels: selectedSeveritiesRef.current,
        chunk: currentChunk,
      };

      try {
        const response = await fetcherClient<S3EventFeedResponse>(
          `${API_BASE_URL}/s3-events/fetch-events/`,
          token,
          {
            method: 'PUT',
            body: payload,
            signal: controller.signal, // Pass the signal to the fetch request
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
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (error: any) {
        if (error.name === 'AbortError') {
          console.log('Fetch request aborted.');
        } else {
          console.error('Failed to fetch events:', error);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    },
    [token, organizationId, machines],
  );

  useEffect(() => {
    // When filters change, reset the feed and fetch the first chunk
    setS3FeedEvents(undefined);
    setChunk(1);
    fetchEvents(1);

    // Cleanup function to abort the fetch request if the component unmounts
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
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
          // Use the current chunk value from s3FeedEvents or fall back to chunk state
          const nextChunk = (s3FeedEvents?.chunk || chunk) + 1;
          fetchEvents(nextChunk);
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
      const nextChunk = (s3FeedEvents?.chunk || chunk) + 1;
      fetchEvents(nextChunk);
    }
  };

  const handleTagToggle = useCallback((tagId: number) => {
    setSelectedTags((prev) => {
      const newTags = prev.includes(tagId)
        ? prev.filter((id) => id !== tagId)
        : [...prev, tagId];
      return newTags;
    });
  }, []);

  const handleSeverityToggle = useCallback((severityId: number) => {
    setSelectedSeverities((prev) => {
      const newSeverities = prev.includes(severityId)
        ? prev.filter((id) => id !== severityId)
        : [...prev, severityId];
      return newSeverities;
    });
  }, []);

  const clearTagFilters = useCallback(() => {
    setSelectedTags([]);
  }, []);

  const clearSeverityFilters = useCallback(() => {
    setSelectedSeverities([]);
  }, []);

  const clearAllFilters = useCallback(() => {
    setSelectedTags([]);
    setSelectedSeverities([]);
  }, []);

  return (
    <div className="space-y-4 p-4">
      <FilterEvents
        search={search}
        setSearch={setSearch}
        selectedTags={selectedTags}
        selectedSeverities={selectedSeverities}
        allTags={allTags}
        onTagToggle={handleTagToggle}
        onSeverityToggle={handleSeverityToggle}
        onStartDateChange={handleStartDateChange}
        onEndDateChange={handleEndDateChange}
        onClearTagFilters={clearTagFilters}
        onClearSeverityFilters={clearSeverityFilters}
        onClearAllFilters={clearAllFilters}
      />

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
