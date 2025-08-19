'use client';

import React from 'react';
import { Info } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

import { FeedEvent } from '@/lib/types/activity';
import { cn, toTitleCase, formatUnixTimestamp } from '@/lib/utils';
import { getSeverityLabel } from '@/lib/utils/severity';

import EventImage from './event-image';

export default function EventDetails({ event }: { event: FeedEvent }) {
  return (
    <div className="flex-1 space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <h4 className="text-muted-foreground text-sm font-semibold">
          Event Severity
        </h4>
        <p>
          {(() => {
            const { label, className, description } = getSeverityLabel(
              event.severity,
            );
            return (
              <Badge className={cn(className)}>
                {label}
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-4 w-4" />
                  </TooltipTrigger>
                  <TooltipContent>{description}</TooltipContent>
                </Tooltip>
              </Badge>
            );
          })()}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <h4 className="text-muted-foreground text-sm font-semibold">
          Machine ID
        </h4>
        <p>{event.machine_id}</p>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <h4 className="text-muted-foreground text-sm font-semibold">
          Timestamp
        </h4>
        <p>
          {formatUnixTimestamp(event.timestamp)}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-muted col-span-full h-full space-y-2 rounded-md p-2">
          <h4 className="text-muted-foreground text-sm font-semibold">
            Detected Objects
          </h4>
          <div className="flex flex-wrap gap-2 overflow-x-auto overflow-y-auto">
            {event.cropped_images.map((detectedObject, index) => {
              return (
                <div key={index}>
                  <EventImage
                    className="h-[100px] w-auto rounded-md object-contain"
                    path={detectedObject.image_file_path}
                  />
                  <span className="text-muted-foreground text-sm">
                    {toTitleCase(detectedObject.class_name)}(
                    {(detectedObject.confidence * 100).toPrecision(2)}
                    %)
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
