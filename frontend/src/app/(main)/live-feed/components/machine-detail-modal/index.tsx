import React, { useCallback, useMemo, useState } from 'react';
import useOrganization from '@/hooks/use-organization';
import { usePubSub } from '@/hooks/use-pub-sub';
import useToken from '@/hooks/use-token';
import { Camera } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { Machine } from '@/lib/types/machine';
import { toTitleCase } from '@/lib/utils';

import HistoricalEventsTab from './historical-events-tab';
import ImageViewer from './image-viewer';
import LiveEventsTab from './live-events-tab';
import MachineInfoHeader from './machine-info-header';

interface MachineEvent {
  id: string;
  timestamp: Date;
  eventstr: string;
  image_c_key?: string;
  image_f_key?: string;
  cropped_image_url?: string;
  full_image_url?: string;
  images_loaded: boolean;
  images_requested: boolean;
  event_severity?: string;
}

interface EventMessage {
  image_c_key: string;
  image_f_key: string;
  event_severity: string;
}

interface MachineDetailModalProps {
  selectedMachine: Machine | null;
  setSelectedMachine: React.Dispatch<React.SetStateAction<Machine | null>>;
  getMachineData: (machineId: number) => { buffer_size: number } | undefined;
}

const fetchEventImages = async (
  token: string,
  imageKeys: { image_c_key: string; image_f_key: string },
) => {
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
    }
    throw new Error(data?.error || 'Failed to fetch images');
  } catch (error) {
    console.error('Error fetching images:', error);
    return null;
  }
};

export default function MachineDetailModal({
  selectedMachine,
  setSelectedMachine,
  getMachineData,
}: MachineDetailModalProps) {
  const { token } = useToken();
  const { organizationId } = useOrganization();
  const [selectedImageUrl, setSelectedImageUrl] = useState<string | null>(null);
  const [liveEventsByMachine, setLiveEventsByMachine] = useState<
    Record<number, MachineEvent[]>
  >({});

  const mqttTopics = useMemo(() => {
    if (!selectedMachine || !organizationId) return [];
    const today = new Date().toISOString().split('T')[0];
    return [
      `${organizationId}/_all_/${today}/${selectedMachine.id}/_all_/EVENT/#`,
    ];
  }, [organizationId, selectedMachine]);

  const handleMqttMessage = useCallback(
    async (topic: string, data: EventMessage) => {
      if (!token || !selectedMachine) return;
      const machineId = selectedMachine.id;

      const newEvent: MachineEvent = {
        id: `live-${Date.now()}`,
        timestamp: new Date(),
        eventstr: `Event - Severity ${data.event_severity}`,
        image_c_key: data.image_c_key,
        image_f_key: data.image_f_key,
        images_loaded: false,
        images_requested: true, // Immediately requested
        event_severity: data.event_severity,
      };

      setLiveEventsByMachine((prev) => {
        const currentEvents = prev[machineId] || [];
        const updatedEvents = [newEvent, ...currentEvents].slice(0, 3);
        return { ...prev, [machineId]: updatedEvents };
      });

      const imageUrls = await fetchEventImages(token, {
        image_c_key: data.image_c_key,
        image_f_key: data.image_f_key,
      });

      setLiveEventsByMachine((prev) => {
        const currentEvents = prev[machineId] || [];
        const updatedEvents = currentEvents.map((e) =>
          e.id === newEvent.id
            ? { ...e, ...imageUrls, images_loaded: true }
            : e,
        );
        return { ...prev, [machineId]: updatedEvents };
      });
    },
    [token, selectedMachine],
  );

  const { isConnected, error: mqttError } = usePubSub(
    mqttTopics,
    handleMqttMessage,
  );

  if (!selectedMachine) return null;

  const machineData = getMachineData(selectedMachine.id);
  const liveEvents = liveEventsByMachine[selectedMachine.id] || [];

  return (
    <>
      <Dialog
        open={!!selectedMachine}
        onOpenChange={() => setSelectedMachine(null)}
      >
        <DialogContent className="flex h-full max-h-[95vh] w-full max-w-6xl flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-xl">
              <Camera className="h-6 w-6 text-blue-600" />
              {toTitleCase(selectedMachine.name)}
              {liveEvents.length > 0 && (
                <Badge variant="destructive" className="animate-pulse">
                  {liveEvents.length} Live Event{liveEvents.length > 1 && 's'}
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>

          <div className="flex-grow space-y-4 overflow-y-auto p-1 pr-2">
            <MachineInfoHeader
              machine={selectedMachine}
              bufferSize={machineData?.buffer_size ?? 0}
              mqttConnected={isConnected}
            />

            <Separator />

            <Tabs defaultValue="recent" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="recent">Live Events</TabsTrigger>
                <TabsTrigger value="historical">
                  Historical Events (7d)
                </TabsTrigger>
              </TabsList>
              <TabsContent value="recent" className="mt-4">
                <LiveEventsTab
                  events={liveEvents}
                  mqttConnected={isConnected}
                  mqttError={mqttError}
                  onImageClick={setSelectedImageUrl}
                />
              </TabsContent>
              <TabsContent value="historical" className="mt-4">
                <HistoricalEventsTab
                  machineId={selectedMachine.id}
                  token={token}
                  orgId={organizationId}
                  onImageClick={setSelectedImageUrl}
                />
              </TabsContent>
            </Tabs>
          </div>
        </DialogContent>
      </Dialog>

      <ImageViewer
        imageUrl={selectedImageUrl}
        onClose={() => setSelectedImageUrl(null)}
      />
    </>
  );
}
