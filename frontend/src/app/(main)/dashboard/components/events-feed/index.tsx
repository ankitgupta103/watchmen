'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
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
import FilterEvents from '../filter-events';


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
    setS3FeedEvents(undefined);
    setChunk(1);
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
