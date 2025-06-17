'use client';

import { useRef } from 'react';
import L from 'leaflet';
import { renderToString } from 'react-dom/server';
import {
  LayersControl,
  MapContainer,
  Marker,
  Popup,
  ScaleControl,
  ZoomControl,
} from 'react-leaflet';
import ReactLeafletGoogleLayer from 'react-leaflet-google-layer';

import { Badge } from '@/components/ui/badge';

import 'leaflet/dist/leaflet.css';

import { MAPS_API_KEY } from '@/lib/constants';
import { Machine } from '@/lib/types/machine';
import { cn } from '@/lib/utils';

interface MachineEvent {
  id: string;
  timestamp: Date;
  eventstr: string;
  image_c_key?: string;
  image_f_key?: string;
  cropped_image_url?: string;
  full_image_url?: string;
  images_loaded?: boolean;
}

interface SimpleMachineData {
  machine_id: number;
  events: MachineEvent[];
  event_count: number;
  last_event?: MachineEvent;
  last_updated: string;
  // Status and location from useMachineStats
  is_online: boolean;
  location: { lat: number; lng: number };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  stats_data: any;
  buffer_size: number;
}

interface MapProps {
  machines: Machine[];
  onMarkerClick: (machine: Machine) => void;
  getMachineData: (machineId: number) => SimpleMachineData;
}

// Get color based on event count
const getEventColor = (eventCount: number) => {
  if (eventCount === 0)
    return {
      bg: 'bg-blue-500',
      border: 'border-blue-600',
      text: 'text-blue-100',
    };
  if (eventCount <= 3)
    return {
      bg: 'bg-yellow-500',
      border: 'border-yellow-600',
      text: 'text-yellow-100',
    };
  if (eventCount <= 7)
    return {
      bg: 'bg-orange-500',
      border: 'border-orange-600',
      text: 'text-orange-100',
    };
  if (eventCount <= 12)
    return { bg: 'bg-red-500', border: 'border-red-600', text: 'text-red-100' };
  return { bg: 'bg-red-700', border: 'border-red-800', text: 'text-red-100' };
};

// Create enhanced custom icon with event-based coloring
const createEventIcon = (machine: Machine, machineData: SimpleMachineData) => {
  const eventCount = machineData.event_count;
  const colors = getEventColor(eventCount);
  const isOffline = !machineData.is_online; // Use the correct status from useMachineStats

  // Override colors if machine is offline
  const finalColors = isOffline
    ? { bg: 'bg-gray-500', border: 'border-gray-600', text: 'text-gray-100' }
    : colors;

  const iconHtml = renderToString(
    <div className="relative">
      {/* Pulse animation for machines with events */}
      {!isOffline && eventCount > 0 && (
        <div
          className={`absolute inset-0 rounded-full ${finalColors.bg} animate-ping opacity-75`}
        ></div>
      )}

      {/* Main marker */}
      <div
        className={cn(
          `relative flex h-8 w-8 items-center justify-center rounded-full border-2 border-white shadow-lg`,
          finalColors.bg,
        )}
      >
        <div className="h-2 w-2 rounded-full bg-white"></div>
      </div>

      {/* Event count indicator */}
      {eventCount > 0 && (
        <div
          className={cn(
            'absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full border border-white text-xs font-bold shadow-sm',
            eventCount <= 3
              ? 'bg-yellow-600 text-white'
              : eventCount <= 7
                ? 'bg-orange-600 text-white'
                : eventCount <= 12
                  ? 'bg-red-600 text-white'
                  : 'bg-red-800 text-white',
          )}
        >
          {eventCount > 99 ? '99+' : eventCount}
        </div>
      )}

      {/* Offline indicator */}
      {isOffline && (
        <div className="absolute -right-1 -bottom-1 flex h-3 w-3 items-center justify-center rounded-full border border-white bg-gray-700">
          <div className="h-1 w-1 rounded-full bg-white"></div>
        </div>
      )}
    </div>,
  );

  return L.divIcon({
    html: iconHtml,
    iconSize: [32, 32],
    popupAnchor: [0, -16],
    className: 'custom-event-marker',
  });
};

// Calculate map center
function getMapCenter(
  machines: Machine[],
  getMachineData: (id: number) => SimpleMachineData,
): [number, number] {
  if (machines.length === 0) return [12.9716, 77.5946]; // Default to Bangalore

  const bounds = machines.reduce(
    (acc, m) => {
      const machineData = getMachineData(m.id);
      return {
        minLat: Math.min(acc.minLat, machineData.location.lat),
        maxLat: Math.max(acc.maxLat, machineData.location.lat),
        minLng: Math.min(acc.minLng, machineData.location.lng),
        maxLng: Math.max(acc.maxLng, machineData.location.lng),
      };
    },
    {
      minLat: getMachineData(machines[0].id).location.lat,
      maxLat: getMachineData(machines[0].id).location.lat,
      minLng: getMachineData(machines[0].id).location.lng,
      maxLng: getMachineData(machines[0].id).location.lng,
    },
  );

  return [
    (bounds.minLat + bounds.maxLat) / 2,
    (bounds.minLng + bounds.maxLng) / 2,
  ];
}

// Calculate optimal zoom level
function getOptimalZoom(
  machines: Machine[],
  getMachineData: (id: number) => SimpleMachineData,
): number {
  if (machines.length <= 1) return 12;

  const bounds = machines.reduce(
    (acc, m) => {
      const machineData = getMachineData(m.id);
      return {
        minLat: Math.min(acc.minLat, machineData.location.lat),
        maxLat: Math.max(acc.maxLat, machineData.location.lat),
        minLng: Math.min(acc.minLng, machineData.location.lng),
        maxLng: Math.max(acc.maxLng, machineData.location.lng),
      };
    },
    {
      minLat: getMachineData(machines[0].id).location.lat,
      maxLat: getMachineData(machines[0].id).location.lat,
      minLng: getMachineData(machines[0].id).location.lng,
      maxLng: getMachineData(machines[0].id).location.lng,
    },
  );

  const latDiff = bounds.maxLat - bounds.minLat;
  const lngDiff = bounds.maxLng - bounds.minLng;
  const maxDiff = Math.max(latDiff, lngDiff);

  if (maxDiff > 1) return 8;
  if (maxDiff > 0.5) return 10;
  if (maxDiff > 0.1) return 12;
  return 14;
}

// Enhanced Marker Component
interface EnhancedMarkerProps {
  machine: Machine;
  machineData: SimpleMachineData;
  onMarkerClick: (machine: Machine) => void;
}

function EnhancedMarker({
  machine,
  machineData,
  onMarkerClick,
}: EnhancedMarkerProps) {
  const markerRef = useRef<L.Marker>(null);
  let hoverTimeout: NodeJS.Timeout;

  const handleMouseOver = () => {
    if (hoverTimeout) {
      clearTimeout(hoverTimeout);
    }

    if (markerRef.current) {
      markerRef.current.openPopup();
    }
  };

  const handleMouseOut = () => {
    hoverTimeout = setTimeout(() => {
      if (markerRef.current) {
        markerRef.current.closePopup();
      }
    }, 100);
  };

  const handleClick = () => {
    if (markerRef.current) {
      markerRef.current.closePopup();
    }
    onMarkerClick(machine);
  };

  const getEventLevelText = (count: number) => {
    if (count === 0) return 'No events';
    if (count <= 3) return 'Low activity';
    if (count <= 7) return 'Medium activity';
    if (count <= 12) return 'High activity';
    return 'Critical activity';
  };

  const getEventLevelColor = (count: number) => {
    if (count === 0) return 'text-blue-600';
    if (count <= 3) return 'text-yellow-600';
    if (count <= 7) return 'text-orange-600';
    if (count <= 12) return 'text-red-600';
    return 'text-red-800';
  };

  return (
    <Marker
      ref={markerRef}
      icon={createEventIcon(machine, machineData)}
      position={[machineData.location.lat ?? 0, machineData.location.lng ?? 0]}
      eventHandlers={{
        click: handleClick,
        mouseover: handleMouseOver,
        mouseout: handleMouseOut,
      }}
    >
      <Popup
        className="custom-popup"
        closeButton={false}
        autoClose={false}
        closeOnClick={false}
        closeOnEscapeKey={false}
      >
        <div className="mb-2 flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">
            {machine.name.toUpperCase()}
          </h3>
          <Badge
            variant={machineData.is_online ? 'default' : 'destructive'}
            className="text-xs"
          >
            {machineData.is_online ? 'Online' : 'Offline'}
          </Badge>
        </div>

        <div className="space-y-1 text-xs">
          <div>
            <strong>Machine ID:</strong> {machine.id}
          </div>

          <div>
            <strong>Type:</strong> {machine.type.replace('_', ' ')}
          </div>

          {/* Event information */}
          <div
            className={cn(
              'font-medium',
              getEventLevelColor(machineData.event_count),
            )}
          >
            <strong>Events:</strong> {machineData.event_count} (
            {getEventLevelText(machineData.event_count)})
          </div>

          {/* Last event info */}
          {machineData.last_event && (
            <div className="mt-1 border-t pt-1 text-xs text-blue-600">
              <strong>Last Event:</strong> {machineData.last_event.eventstr}
              <br />
              <span className="text-gray-500">
                {new Date(
                  machineData.last_event.timestamp,
                ).toLocaleTimeString()}
              </span>
            </div>
          )}

          <div className="mt-1 border-t pt-1 text-xs text-gray-500">
            <strong>Location:</strong> {machineData.location.lat.toFixed(4)},{' '}
            {machineData.location.lng.toFixed(4)}
          </div>

          <div className="text-xs text-gray-400">Click to view details</div>
        </div>
      </Popup>
    </Marker>
  );
}

export default function SimplifiedReactLeafletMap({
  machines,
  onMarkerClick,
  getMachineData,
}: MapProps) {
  const center = getMapCenter(machines, getMachineData);
  const zoom = getOptimalZoom(machines, getMachineData);

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

      {/* Machine Markers with Event-based Coloring */}
      {machines.map((machine) => (
        <EnhancedMarker
          key={machine.id}
          machine={machine}
          machineData={getMachineData(machine.id)}
          onMarkerClick={onMarkerClick}
        />
      ))}
    </MapContainer>
  );
}
