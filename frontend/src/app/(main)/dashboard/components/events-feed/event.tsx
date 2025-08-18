'use client';

import React from 'react';

import { Badge } from '@/components/ui/badge';

import { FeedEvent } from '@/lib/types/activity';
import { Machine } from '@/lib/types/machine';

import EventDetails from './event-details';
import EventImage from './event-image';

export default function Event({
  event,
  machines,
}: {
  event: FeedEvent;
  machines: Machine[];
}) {
  const machine = machines.find((machine) => machine.id === event.machine_id);

  return (
    <div
      key={event.timestamp.toString()}
      className="space-y-2 rounded-md border p-4"
    >
      <div className="flex gap-2">
        <h3 className="font-mono text-lg font-semibold">{machine?.name}</h3>
        <div className="flex gap-2">
          {machine?.tags?.map((tag) => (
            <Badge variant="outline" key={tag.id}>
              {tag.name}
            </Badge>
          ))}
        </div>
      </div>
      <div className="flex flex-col gap-4 md:flex-row">
        <EventImage
          className="h-[50vh] w-auto rounded-md object-contain"
          path={event?.annotated_image_path ?? event?.original_image_path ?? ''}
        />

        <EventDetails event={event} />
      </div>
    </div>
  );
}
