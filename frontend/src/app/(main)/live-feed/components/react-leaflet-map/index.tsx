'use client';

import {
  LayersControl,
  MapContainer,
  ScaleControl,
  ZoomControl,
} from 'react-leaflet';
import ReactLeafletGoogleLayer from 'react-leaflet-google-layer';

import 'leaflet/dist/leaflet.css';

import { MAPS_API_KEY } from '@/lib/constants';
import { Machine, MachineData } from '@/lib/types/machine';
import { calculateMapCenter, calculateOptimalZoom } from '@/lib/utils';

import MachineMarker from './machine-marker';

interface MapProps {
  machines: Machine[];
  onMarkerClick: (machine: Machine) => void;
  getMachineData: (machineId: number) => MachineData;
}

export default function ReactLeafletMap({
  machines,
  onMarkerClick,
  getMachineData,
}: MapProps) {
  const center = calculateMapCenter(machines);
  const zoom = calculateOptimalZoom(machines);

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

      {/* LayersControl for base layers */}
      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name="Google Maps (Roadmap)">
          <ReactLeafletGoogleLayer apiKey={MAPS_API_KEY} type={'roadmap'} />
        </LayersControl.BaseLayer>

        <LayersControl.BaseLayer name="Google Maps (Satellite)">
          <ReactLeafletGoogleLayer apiKey={MAPS_API_KEY} type={'satellite'} />
        </LayersControl.BaseLayer>

        <LayersControl.BaseLayer name="Google Maps (Hybrid)">
          <ReactLeafletGoogleLayer apiKey={MAPS_API_KEY} type={'hybrid'} />
        </LayersControl.BaseLayer>

        <LayersControl.BaseLayer name="Google Maps (Terrain)">
          <ReactLeafletGoogleLayer apiKey={MAPS_API_KEY} type={'terrain'} />
        </LayersControl.BaseLayer>
      </LayersControl>

      {/* Machine Markers with Status-based Coloring and Pulsating Animation */}
      {machines.map((machine) => (
        <MachineMarker
          key={machine.id}
          machine={machine}
          machineData={getMachineData(machine.id)}
          onMarkerClick={onMarkerClick}
        />
      ))}
    </MapContainer>
  );
}
