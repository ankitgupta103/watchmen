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
  isMachineOnline,
} from '@/lib/utils';

import MachineMarker from './machine-marker';

interface MapProps {
  machines: Machine[];
  machineEvents: Record<number, FeedEvent[]>;
  pulsatingMachines: Record<number, boolean>;
}

export default function ReactLeafletMap({
  machines,
  machineEvents,
  pulsatingMachines,
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

        const machineData: MachineData = {
          machine_id: machine.id,
          events: [],
          event_count: events.length,
          last_event: {
            id: '0',
            machineId: machine.id,
            machineName: machine.name,
            machineType: machine.type,
            timestamp: new Date(lastEvent?.timestamp),
            imagesLoaded: false,
            severity: 0,
            original_image_path: '',
            cropped_images: [],
          },
          last_updated: new Date(lastEvent?.timestamp).toISOString(),
          is_online: isMachineOnline(machine),
          is_pulsating: isPulsating,
          is_critical: lastEvent ? lastEvent.severity >= 3 : false,
          location: { lat: 0, long: 0, timestamp: '' },
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
