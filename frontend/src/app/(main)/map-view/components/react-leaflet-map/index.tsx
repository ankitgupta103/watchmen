'use client';

import {
  LayersControl,
  MapContainer,
  ScaleControl,
  ZoomControl,
} from 'react-leaflet';
import ReactLeafletGoogleLayer from 'react-leaflet-google-layer';

import 'leaflet/dist/leaflet.css';
import './map-styles.css';

import { MAPS_API_KEY } from '@/lib/constants';
import { FeedEvent } from '@/lib/types/activity';
import { Machine, MachineData } from '@/lib/types/machine';
import {
  calculateMapCenter,
  calculateOptimalZoom,
} from '@/lib/utils';

import MachineMarker from './machine-marker';

interface MapProps {
  machines: Machine[];
  machineEvents: Record<number, FeedEvent[]>;
  pulsatingMachines: Record<number, boolean>;
  getDeviceStatus: (machine: Machine) => 'online' | 'offline';
}

export default function ReactLeafletMap({
  machines,
  machineEvents,
  pulsatingMachines,
  getDeviceStatus,
}: MapProps) {
  const center = calculateMapCenter(machines);
  const zoom = calculateOptimalZoom(machines);

  // Debug logging
  console.log('🗺️ [MapView] Rendering map with:', {
    machinesCount: machines.length,
    machineEvents: Object.keys(machineEvents).length,
    pulsatingMachines: Object.keys(pulsatingMachines).length,
    pulsatingMachinesState: pulsatingMachines,
  });

  return (
    <MapContainer
      style={{ height: '100%', width: '100%' }}
      zoom={zoom}
      center={center}
      zoomControl={false}
      className="h-full w-full"
    >
      <ZoomControl position="topleft" />
      <ScaleControl position="bottomleft" />

      {/* Simplified layer control */}
      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name="Satellite">
          <ReactLeafletGoogleLayer apiKey={MAPS_API_KEY} type={'satellite'} />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Roadmap">
          <ReactLeafletGoogleLayer apiKey={MAPS_API_KEY} type={'roadmap'} />
        </LayersControl.BaseLayer>
      </LayersControl>

      {/* Machine markers */}
      {machines.map((machine) => {
        const events = machineEvents[machine.id] || [];
        const lastEvent = events[0];
        const isPulsating = pulsatingMachines[machine.id] || false;

        console.log(`🔍 [MapView] Creating marker for machine ${machine.id}:`, {
          isPulsating,
          pulsatingMachinesState: pulsatingMachines,
          machineId: machine.id,
        });

        // Convert FeedEvent from activity.ts to the format expected by MachineData
        const convertedEvents = events.map(event => ({
          id: `${event.machine_id}_${event.timestamp}`,
          machineId: event.machine_id,
          machineName: machine.name,
          machineType: machine.type,
          timestamp: new Date(event.timestamp * 1000),
          original_image_path: event.original_image_path,
          cropped_images: event.cropped_images,
          fullImageUrl: event.annotated_image_path || event.original_image_path,
          croppedImageUrls: [],
          imagesLoaded: false,
          severity: event.severity,
        }));

        const machineData: MachineData = {
          machine_id: machine.id,
          events: convertedEvents,
          event_count: events.length,
          last_event: lastEvent ? convertedEvents[0] : undefined,
          last_updated: lastEvent ? new Date(lastEvent.timestamp * 1000).toISOString() : new Date().toISOString(),
          is_online: getDeviceStatus(machine) === 'online',
          is_pulsating: isPulsating,
          is_critical: lastEvent ? lastEvent.severity >= 3 : false,
          location: machine.last_location,
          stats_data: {},
          buffer_size: 0,
        };

        return (
          <MachineMarker
            key={machine.id}
            machine={machine}
            machineData={machineData}
          />
        );
      })}
    </MapContainer>
  );
}
