'use client';

import React, { useEffect, useState, memo } from 'react';
import { Calendar, Camera, Clock } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';

import { cn } from '@/lib/utils';
import LiveEventImage from './live-events-image';



interface MachineEvent {
  id: string;
  timestamp: Date;
  eventstr: string;
  image_c_key?: string;
  image_f_key?: string;
  event_severity?: string;
}

interface LiveEventsTabProps {
  events: MachineEvent[];
  mqttConnected: boolean;
  mqttError: Error | null;
  onImageClick: (url: string) => void;
  token: string | null;
}

const LiveEventsTab = memo(({
  events,
  mqttConnected,
  mqttError,
  onImageClick,
  token,
}: LiveEventsTabProps) => {
  const [relativeTimes, setRelativeTimes] = useState<Record<string, string>>({});

  useEffect(() => {
    const calculateAllRelativeTimes = () => {
      const now = new Date().getTime();
      const newRelativeTimes: Record<string, string> = {};

      for (const event of events) {
        const diff = now - event.timestamp.getTime();
        const minutes = Math.floor(diff / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);

        if (minutes > 0) {
          newRelativeTimes[event.id] = `${minutes}m ${seconds}s ago`;
        } else {
          newRelativeTimes[event.id] = `${Math.max(0, seconds)}s ago`;
        }
      }
      setRelativeTimes(newRelativeTimes);
    };

    calculateAllRelativeTimes();
    const intervalId = setInterval(calculateAllRelativeTimes, 5000);
    return () => clearInterval(intervalId);
  }, [events]);

  return (
    <div className="space-y-4">
      {mqttError && (
        <div className="rounded-lg border-l-4 border-l-red-500 bg-red-50/30 p-3 text-sm text-red-700">
          MQTT Connection Error: {mqttError.message}
        </div>
      )}
      
      {events.length === 0 ? (
        <div className="py-12 text-center">
          <Camera className="mx-auto mb-4 h-16 w-16 text-gray-300" />
          <h3 className="mb-2 text-lg font-medium text-gray-600">
            No Live Events
          </h3>
          <p className="text-sm text-gray-500">
            {mqttConnected
              ? 'Waiting for live events from this machine...'
              : 'Connecting to MQTT to receive live events...'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {events.map((event) => (
            <Card
              key={event.id}
              className={cn(
                'border-l-4',
                event?.event_severity === '1' &&
                  'border-l-yellow-500 bg-yellow-50/30',
                event?.event_severity === '2' &&
                  'border-l-orange-600 bg-orange-50/30',
                event?.event_severity === '3' &&
                  'border-l-red-700 bg-red-50/30',
              )}
            >
              <CardContent className="space-y-3 p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <Badge variant="default" className="bg-green-600">
                      Live
                    </Badge>
                    <span className="font-medium">{event.eventstr}</span>
                  </div>
                  <span className="flex items-center gap-1 text-xs text-gray-500">
                    <Clock className="h-3 w-3" />
                    {relativeTimes[event.id] || '...'}
                  </span>
                </div>
                
                <div className="flex items-center gap-2">
                  <span>Event Severity: </span>
                  <Badge
                    variant="outline"
                    className={cn(
                      event?.event_severity === '1' &&
                        'border-yellow-500 bg-yellow-400 text-black',
                      event?.event_severity === '2' &&
                        'border-orange-600 bg-orange-500 text-white',
                      event?.event_severity === '3' &&
                        'border-red-700 bg-red-600 text-white',
                    )}
                  >
                    {event?.event_severity === '1'
                      ? 'Low'
                      : event?.event_severity === '2'
                        ? 'High'
                        : 'Critical'}
                  </Badge>
                </div>


                <LiveEventImage
                  token={token}
                  image_c_key={event.image_c_key}
                  image_f_key={event.image_f_key}
                  onImageClick={onImageClick}
                  eventId={event.id}
                />

                <div className="flex items-center gap-2 pt-1 text-xs text-gray-500">
                  <Calendar className="h-3 w-3" />
                  <span>{event.timestamp.toLocaleString()}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
});

LiveEventsTab.displayName = 'LiveEventsTab';

export default LiveEventsTab;