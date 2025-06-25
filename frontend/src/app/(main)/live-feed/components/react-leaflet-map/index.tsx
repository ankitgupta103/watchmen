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
import MachineConnections from './machine-connections';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

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
  const router = useRouter();
  const center = calculateMapCenter(machines);
  const zoom = calculateOptimalZoom(machines);

  useEffect(() => {
    const interval = setInterval(() => {
      router.refresh();
    }, 5000 ); // 5 seconds
    return () => clearInterval(interval);
  }, [router]);

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
        <LayersControl.BaseLayer  checked name="Google Maps (Satellite)">
          <ReactLeafletGoogleLayer apiKey={MAPS_API_KEY} type={'satellite'} />
        </LayersControl.BaseLayer>

        <LayersControl.BaseLayer name="Google Maps (Roadmap)">
          <ReactLeafletGoogleLayer apiKey={MAPS_API_KEY} type={'roadmap'} />
        </LayersControl.BaseLayer>

        <LayersControl.BaseLayer name="Google Maps (Hybrid)">
          <ReactLeafletGoogleLayer apiKey={MAPS_API_KEY} type={'hybrid'} />
        </LayersControl.BaseLayer>

        <LayersControl.BaseLayer name="Google Maps (Terrain)">
          <ReactLeafletGoogleLayer apiKey={MAPS_API_KEY} type={'terrain'} />
        </LayersControl.BaseLayer>
      </LayersControl>

      {/* Machine Connections with Animated Dashed Lines */}
      <MachineConnections machines={machines} />

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