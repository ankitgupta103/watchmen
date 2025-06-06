'use client';

import { useRef } from 'react';
import L from 'leaflet';
// import { Activity, AlertTriangle, Eye, MapPin, Shield } from 'lucide-react';
import { renderToString } from 'react-dom/server';
import {
  Circle,
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
import { Machine, MachineData } from '@/lib/types/machine';
import { cn } from '@/lib/utils';

interface MapProps {
  machines: Machine[];
  onMarkerClick: (machine: Machine) => void;
  selectedDate?: Date;
  getMachineData: (machineId: number) => MachineData;
}

// Calculate machine activity level
const getMachineActivityLevel = (data: MachineData) => {
  const recentEvents =
    data.suspiciousEvents?.filter((event) => {
      const eventDate = new Date(event.timestamp);
      const daysDiff =
        (Date.now() - eventDate.getTime()) / (1000 * 60 * 60 * 24);
      return daysDiff <= 7;
    }) || [];

  const healthIssues =
    data.healthEvents?.filter(
      (event) => event.severity === 'high' || event.severity === 'critical',
    ) || [];

  if (recentEvents.length > 5 || healthIssues.length > 0) return 'critical';
  if (recentEvents.length > 2) return 'high';
  if (recentEvents.length > 0) return 'medium';
  return 'low';
};

// Get unreviewed events count
const getUnreviewedCount = (data: MachineData) => {
  return (
    data.suspiciousEvents?.filter(
      (event) => event.marked === 'unreviewed' || !event.marked,
    ).length || 0
  );
};

// Create enhanced custom icon with activity indicators
const createEnhancedIcon = (machine: Machine, machineData: MachineData) => {
  const activityLevel = getMachineActivityLevel(machineData);
  const unreviewed = getUnreviewedCount(machineData);
  const isOffline = machineData.status === 'offline';
  const isMaintenance = machineData.status === 'maintenance';

  // Determine colors based on status and activity
  let bgColor = 'bg-green-500';

  if (isOffline) {
    bgColor = 'bg-gray-500';
  } else if (isMaintenance) {
    bgColor = 'bg-yellow-500';
  } else if (activityLevel === 'critical') {
    bgColor = 'bg-red-500';
  } else if (activityLevel === 'high') {
    bgColor = 'bg-orange-500';
  } else if (activityLevel === 'medium') {
    bgColor = 'bg-yellow-500';
  }

  const iconHtml = renderToString(
    <div className="relative">
      {/* Pulse animation for critical/active machines */}
      {machineData.status !== 'offline' && activityLevel !== 'low' && (
        <div
          className={`absolute inset-0 rounded-full ${bgColor} animate-ping opacity-90`}
        ></div>
      )}

      {/* Main marker */}
      <div
        className={cn(
          `relative flex h-5 w-5 items-center justify-center rounded-full border-white bg-yellow-500 font-extrabold text-white shadow-lg`,
          {
            'bg-green-500': machineData.status === 'online',
            'bg-gray-500': machineData.status === 'offline',
          },
        )}
      >
        {unreviewed > 9 ? '9+' : unreviewed}
      </div>
    </div>,
  );

  return L.divIcon({
    html: iconHtml,
    iconSize: [20, 20],
    popupAnchor: [0, -10],
    className: 'custom-enhanced-marker',
  });
};

// Calculate map center with better positioning
function getMapCenter(machines: Machine[]): [number, number] {
  if (machines.length! > 0) return [12.9716, 77.5946]; // Default to Bangalore

  const bounds = machines.reduce(
    (acc, m) => ({
      minLat: Math.min(acc.minLat, m.last_location?.lat ?? 0),
      maxLat: Math.max(acc.maxLat, m.last_location?.lat ?? 0),
      minLng: Math.min(acc.minLng, m.last_location?.lng ?? 0),
      maxLng: Math.max(acc.maxLng, m.last_location?.lng ?? 0),
    }),
    {
      minLat: machines[0]?.last_location?.lat ?? 0,
      maxLat: machines[0]?.last_location?.lat ?? 0,
      minLng: machines[0]?.last_location?.lng ?? 0,
      maxLng: machines[0]?.last_location?.lng ?? 0,
    },
  );

  return [
    (bounds.minLat + bounds.maxLat) / 2,
    (bounds.minLng + bounds.maxLng) / 2,
  ];
}

// Calculate optimal zoom level
function getOptimalZoom(machines: Machine[]): number {
  if (machines.length <= 1) return 12;

  const bounds = machines.reduce(
    (acc, m) => ({
      minLat: Math.min(acc.minLat, m.last_location?.lat ?? 0),
      maxLat: Math.max(acc.maxLat, m.last_location?.lat ?? 0),
      minLng: Math.min(acc.minLng, m.last_location?.lng ?? 0),
      maxLng: Math.max(acc.maxLng, m.last_location?.lng ?? 0),
    }),
    {
      minLat: machines[0]?.last_location?.lat ?? 0,
      maxLat: machines[0]?.last_location?.lat ?? 0,
      minLng: machines[0]?.last_location?.lng ?? 0,
      maxLng: machines[0]?.last_location?.lng ?? 0,
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

// Enhanced Marker Component with hover popup functionality
interface EnhancedMarkerProps {
  machine: Machine;
  machineData: MachineData;
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
    // Clear any existing timeout
    if (hoverTimeout) {
      clearTimeout(hoverTimeout);
    }

    // Open popup immediately on hover
    if (markerRef.current) {
      markerRef.current.openPopup();
    }
  };

  const handleMouseOut = () => {
    // Close popup with a slight delay to prevent flickering
    hoverTimeout = setTimeout(() => {
      if (markerRef.current) {
        markerRef.current.closePopup();
      }
    }, 100);
  };

  const handleClick = () => {
    // Close popup and open modal
    if (markerRef.current) {
      markerRef.current.closePopup();
    }
    onMarkerClick(machine);
  };

  return (
    <Marker
      ref={markerRef}
      icon={createEnhancedIcon(machine, machineData)}
      position={[
        machine.last_location?.lat ?? 0,
        machine.last_location?.lng ?? 0,
      ]}
      eventHandlers={{
        click: handleClick,
        mouseover: handleMouseOver,
        mouseout: handleMouseOut,
      }}
    >
      {/* Enhanced Popup with quick info */}
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
            variant={
              machineData.status === 'online'
                ? 'default'
                : machineData.status === 'offline'
                  ? 'destructive'
                  : 'secondary'
            }
            className="text-xs"
          >
            {machineData.status}
          </Badge>
        </div>

        <div className="space-y-1 text-xs">
          <div>
            <strong>Type:</strong> {machine.type.replace('_', ' ')}
          </div>
          <div>
            <strong>Activity:</strong> {getMachineActivityLevel(machineData)}
          </div>
          {machineData.suspiciousEvents &&
            machineData.suspiciousEvents.length > 0 && (
              <div>
                <strong>Recent Events:</strong>{' '}
                {
                  machineData.suspiciousEvents.filter((e) => {
                    const days =
                      (Date.now() - new Date(e.timestamp).getTime()) /
                      (1000 * 60 * 60 * 24);
                    return days <= 7;
                  }).length
                }{' '}
                (last 7 days)
              </div>
            )}
          {getUnreviewedCount(machineData) > 0 && (
            <div className="font-medium text-red-600">
              {getUnreviewedCount(machineData)} unreviewed alert
              {getUnreviewedCount(machineData) > 1 ? 's' : ''}
            </div>
          )}
          <div className="text-xs text-gray-500">
            <strong>Last seen:</strong>{' '}
            {new Date(machineData.lastSeen).toLocaleString()}
          </div>
        </div>
      </Popup>
    </Marker>
  );
}

export default function EnhancedReactLeafletMap({
  machines,
  onMarkerClick,
  getMachineData,
}: MapProps) {
  const center = getMapCenter(machines);
  const zoom = getOptimalZoom(machines);

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

      {/* Enhanced Machine Markers with hover popups */}
      {machines.map((machine) => (
        <EnhancedMarker
          key={machine.id}
          machine={machine}
          machineData={getMachineData(machine.id)}
          onMarkerClick={onMarkerClick}
        />
      ))}

      {/* Coverage Areas for Offline Machines (Dark Spots) */}
      {machines
        .filter((m) => getMachineData(m.id).status === 'offline')
        .map((machine) => (
          <Circle
            key={`dark-${machine.id}`}
            center={[
              machine.last_location?.lat ?? 0,
              machine.last_location?.lng ?? 0,
            ]}
            radius={800}
            pathOptions={{
              fillColor: '#1f2937',
              fillOpacity: 0.15,
              color: '#374151',
              weight: 1,
              opacity: 0.6,
              dashArray: '5, 5',
            }}
          />
        ))}
    </MapContainer>
  );
}
