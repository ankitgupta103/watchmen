'use client';

import React, { useCallback, useState } from 'react';
import { useMachineStats } from '@/hooks/use-machine-stats';
import useToken from '@/hooks/use-token';
import { X } from 'lucide-react';

import { Button } from '@/components/ui/button';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { Machine, MQTTEvent } from '@/lib/types/machine';
import { calculateSeverity } from '@/lib/utils/severity';

import PageHeader from '../page-header';
import DeviceInfo from './device-info';
import EventDetailsModal from './event-details-modal';
import EventsSection from './events-section';
import MQTTEventFeed from './mqtt-event-feed';

interface S3EventData {
  image_c_key: string;
  image_f_key: string;
  eventstr: string;
  timestamp?: string | Date;
  machineId?: number;
}

interface ProcessedEvent extends S3EventData {
  id: string;
  machineId: number;
  timestamp: string | Date;
  croppedImageUrl?: string;
  fullImageUrl?: string;
  imagesFetched: boolean;
  fetchingImages: boolean;
}

interface DeviceDetailsClientProps {
  device: Machine;
  orgId: number;
}

// --- API HELPER FUNCTIONS ---

const fetchEventImages = async (
  token: string | null,
  imageKeys: { image_c_key: string; image_f_key: string },
) => {
  if (!token) {
    console.error('No authentication token available');
    return null;
  }
  try {
    const data = await fetcherClient<{
      success: boolean;
      cropped_image_url?: string;
      full_image_url?: string;
      error?: string;
    }>(`${API_BASE_URL}/event-images/`, token, {
      method: 'POST',
      body: imageKeys,
    });

    if (data?.success) {
      return {
        croppedImageUrl: data.cropped_image_url,
        fullImageUrl: data.full_image_url,
      };
    } else {
      throw new Error(data?.error || 'Failed to fetch images');
    }
  } catch (error) {
    console.error('Error fetching images:', error);
    return null;
  }
};

export default function DeviceDetailsClient({
  device,
  orgId,
}: DeviceDetailsClientProps) {
  const { token } = useToken();
  const { data: machineStats, buffer } = useMachineStats(device.id);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<ProcessedEvent | null>(
    null,
  );
  const [mqttEvents, setMqttEvents] = useState<MQTTEvent[]>([]);
  const [showMqttFeed, setShowMqttFeed] = useState(false);

  const handleFetchModalImages = useCallback(
    async (event: ProcessedEvent): Promise<ProcessedEvent | void> => {
      setSelectedEvent({ ...event, fetchingImages: true });
      const imageUrls = await fetchEventImages(token, {
        image_c_key: event.image_c_key,
        image_f_key: event.image_f_key,
      });

      if (imageUrls) {
        const updatedEvent = {
          ...event,
          ...imageUrls,
          imagesFetched: true,
          fetchingImages: false,
        };
        setSelectedEvent(updatedEvent);
        return updatedEvent;
      } else {
        setSelectedEvent({ ...event, fetchingImages: false });
      }
    },
    [token],
  );

  const handleNewMqttEvent = useCallback((eventData: Omit<MQTTEvent, 'id' | 'severity'>) => {
    const newEvent: MQTTEvent = {
      ...eventData,
      id: `mqtt-${Date.now()}-${Math.random()}`,
      severity: calculateSeverity(eventData.cropped_images),
    };
    
    setMqttEvents(prevEvents => [newEvent, ...prevEvents].slice(0, 20));
  }, []);

  const simulateMqttEvent = useCallback(() => {
    const sampleEvent = {
      timestamp: new Date(),
      original_image_path: "20/_all_/2025-08-07/228/_all_/images/1754562022_full.jpg",
      cropped_images: [
        {
          class_name: "person",
          confidence: 0.92,
          image_file_path: "20/_all_/2025-08-07/228/_all_/images/1754562022_cropped_0.jpg"
        },
        {
          class_name: Math.random() > 0.5 ? "backpack" : "person",
          confidence: 0.85,
          image_file_path: "20/_all_/2025-08-07/228/_all_/images/1754562022_cropped_1.jpg"
        }
      ],
    };
    handleNewMqttEvent(sampleEvent);
  }, [handleNewMqttEvent]);

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader deviceId={device.id.toString()} deviceName={device.name} />
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-red-800">
              <strong>Error:</strong> {error}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setError(null)}
              className="text-red-600 hover:text-red-800"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <DeviceInfo device={device} machineStats={machineStats} buffer={buffer} />

      <div className="flex gap-2 mb-4">
        <Button
          variant={!showMqttFeed ? "default" : "outline"}
          onClick={() => setShowMqttFeed(false)}
          size="sm"
        >
          Historical Events
        </Button>
        <Button
          variant={showMqttFeed ? "default" : "outline"}
          onClick={() => setShowMqttFeed(true)}
          size="sm"
        >
          Live Activity Feed {mqttEvents.length > 0 && `(${mqttEvents.length})`}
        </Button>
        {showMqttFeed && (
          <Button
            variant="secondary"
            onClick={simulateMqttEvent}
            size="sm"
          >
            + Add Test Event
          </Button>
        )}
      </div>

      {showMqttFeed ? (
        <div className="flex-1 overflow-hidden">
          <MQTTEventFeed events={mqttEvents} />
        </div>
      ) : (
        <EventsSection
          device={device}
          orgId={orgId}
          token={token}
          onEventSelect={setSelectedEvent}
        />
      )}

      {selectedEvent && (
        <EventDetailsModal
          event={selectedEvent}
          device={device}
          onClose={() => setSelectedEvent(null)}
          onFetchImages={handleFetchModalImages}
        />
      )}
    </section>
  );
}
