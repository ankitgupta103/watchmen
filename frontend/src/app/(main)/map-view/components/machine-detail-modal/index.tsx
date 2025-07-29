import React, { useState } from 'react';
import useOrganization from '@/hooks/use-organization';
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
  event_severity?: string;
}

interface MachineDetailModalProps {
  selectedMachine: Machine | null;
  setSelectedMachine: React.Dispatch<React.SetStateAction<Machine | null>>;
  getMachineData: (machineId: number) => { buffer_size: number } | undefined;
  token: string | null;
  liveEvents: MachineEvent[];
  mqttError: Error | null;
}

export default function MachineDetailModal({
  selectedMachine,
  setSelectedMachine,
  getMachineData,
  token,
  liveEvents,
  mqttError,
}: MachineDetailModalProps) {
  const { organizationId } = useOrganization();
  const [selectedImageUrl, setSelectedImageUrl] = useState<string | null>(null);

  if (!selectedMachine) return null;

  const machineData = getMachineData(selectedMachine.id);

  return (
    <>
      <Dialog
        open={!!selectedMachine}
        onOpenChange={() => setSelectedMachine(null)}
      >
        <DialogContent className="flex h-full max-h-[95vh] w-full max-w-6xl flex-col bg-gray-50">
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
                  mqttError={mqttError}
                  onImageClick={setSelectedImageUrl}
                  token={token}
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
