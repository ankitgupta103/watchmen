'use client';

import { useRef } from 'react';
import L from 'leaflet';
import { Activity, AlertTriangle, Eye, MapPin, Shield } from 'lucide-react';
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
import { Machine } from '@/lib/types/machine';

interface MapProps {
  machines: Machine[];
  onMarkerClick: (machine: Machine) => void;
  selectedDate?: Date;
}

// Calculate machine activity level
const getMachineActivityLevel = (machine: Machine) => {
  const recentEvents =
    machine.data.suspiciousEvents?.filter((event) => {
      const eventDate = new Date(event.timestamp);
      const daysDiff =
        (Date.now() - eventDate.getTime()) / (1000 * 60 * 60 * 24);
      return daysDiff <= 7;
    }) || [];

  const healthIssues =
    machine.data.healthEvents?.filter(
      (event) => event.severity === 'high' || event.severity === 'critical',
    ) || [];

  if (recentEvents.length > 5 || healthIssues.length > 0) return 'critical';
  if (recentEvents.length > 2) return 'high';
  if (recentEvents.length > 0) return 'medium';
  return 'low';
};

// Get unreviewed events count
const getUnreviewedCount = (machine: Machine) => {
  return (
    machine.data.suspiciousEvents?.filter(
      (event) => event.marked === 'unreviewed' || !event.marked,
    ).length || 0
  );
};

// Get machine type icon
const getMachineTypeIcon = (type: string, size: number = 8) => {
  switch (type) {
    case 'perimeter_guard':
      return <Shield size={size} className="text-white" />;
    case 'mobile_patrol':
      return <Activity size={size} className="text-white" />;
    case 'fixed_surveillance':
      return <Eye size={size} className="text-white" />;
    case 'roving_sensor':
      return <AlertTriangle size={size} className="text-white" />;
    default:
      return <MapPin size={size} className="text-white" />;
  }
};

// Create enhanced custom icon with activity indicators
const createEnhancedIcon = (machine: Machine) => {
  const activityLevel = getMachineActivityLevel(machine);
  const unreviewed = getUnreviewedCount(machine);
  const isOffline = machine.data.status === 'offline';
  const isMaintenance = machine.data.status === 'maintenance';

  // Determine colors based on status and activity
  let bgColor = 'bg-green-500';
  let pulseClass = '';

  if (isOffline) {
    bgColor = 'bg-gray-500';
  } else if (isMaintenance) {
    bgColor = 'bg-yellow-500';
  } else if (activityLevel === 'critical') {
    bgColor = 'bg-red-500';
    pulseClass = 'animate-pulse';
  } else if (activityLevel === 'high') {
    bgColor = 'bg-orange-500';
  } else if (activityLevel === 'medium') {
    bgColor = 'bg-yellow-500';
  }

  const iconHtml = renderToString(
    <div className="relative">
      {/* Pulse animation for critical/active machines */}
      {machine.data.status === 'online' && activityLevel !== 'low' && (
        <div
          className={`absolute inset-0 rounded-full ${bgColor} animate-ping opacity-30`}
        ></div>
      )}

      {/* Main marker */}
      <div
        className={`relative h-10 w-10 ${bgColor} flex items-center justify-center rounded-full border-2 border-white shadow-lg ${pulseClass}`}
      >
        <MapPin size={20} className="text-white" />
      </div>

      {/* Activity indicator badge */}
      {unreviewed > 0 && (
        <div className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full border border-white bg-red-500 text-xs font-bold text-white">
          {unreviewed > 9 ? '9+' : unreviewed}
        </div>
      )}

      {/* Status indicator */}
      <div
        className={`absolute -right-1 -bottom-1 h-3 w-3 rounded-full border border-white ${
          machine.data.status === 'online'
            ? 'bg-green-400'
            : machine.data.status === 'offline'
              ? 'bg-red-400'
              : 'bg-yellow-400'
        }`}
      ></div>

      {/* Type indicator */}
      <div className="absolute -top-1 -left-1 flex h-4 w-4 items-center justify-center rounded-full border border-white bg-blue-500">
        {getMachineTypeIcon(machine.type, 8)}
      </div>
    </div>,
  );

  return L.divIcon({
    html: iconHtml,
    iconSize: [40, 40],
    iconAnchor: [20, 40],
    popupAnchor: [0, -40],
    className: 'custom-enhanced-marker',
  });
};

// Calculate map center with better positioning
function getMapCenter(machines: Machine[]): [number, number] {
  if (!machines.length) return [12.9716, 77.5946]; // Default to Bangalore

  const bounds = machines.reduce(
    (acc, m) => ({
      minLat: Math.min(acc.minLat, m.location.lat),
      maxLat: Math.max(acc.maxLat, m.location.lat),
      minLng: Math.min(acc.minLng, m.location.lng),
      maxLng: Math.max(acc.maxLng, m.location.lng),
    }),
    {
      minLat: machines[0].location.lat,
      maxLat: machines[0].location.lat,
      minLng: machines[0].location.lng,
      maxLng: machines[0].location.lng,
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
      minLat: Math.min(acc.minLat, m.location.lat),
      maxLat: Math.max(acc.maxLat, m.location.lat),
      minLng: Math.min(acc.minLng, m.location.lng),
      maxLng: Math.max(acc.maxLng, m.location.lng),
    }),
    {
      minLat: machines[0].location.lat,
      maxLat: machines[0].location.lat,
      minLng: machines[0].location.lng,
      maxLng: machines[0].location.lng,
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
  onMarkerClick: (machine: Machine) => void;
}

function EnhancedMarker({ machine, onMarkerClick }: EnhancedMarkerProps) {
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
      icon={createEnhancedIcon(machine)}
      position={[machine.location.lat, machine.location.lng]}
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
        <div className="w-[280px] p-2">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold">
              {machine.name.toUpperCase()}
            </h3>
            <Badge
              variant={
                machine.data.status === 'online'
                  ? 'default'
                  : machine.data.status === 'offline'
                    ? 'destructive'
                    : 'secondary'
              }
              className="text-xs"
            >
              {machine.data.status}
            </Badge>
          </div>

          <div className="space-y-1 text-xs">
            <div>
              <strong>Type:</strong> {machine.type.replace('_', ' ')}
            </div>
            <div>
              <strong>Activity:</strong> {getMachineActivityLevel(machine)}
            </div>
            {machine.data.suspiciousEvents &&
              machine.data.suspiciousEvents.length > 0 && (
                <div>
                  <strong>Recent Events:</strong>{' '}
                  {
                    machine.data.suspiciousEvents.filter((e) => {
                      const days =
                        (Date.now() - new Date(e.timestamp).getTime()) /
                        (1000 * 60 * 60 * 24);
                      return days <= 7;
                    }).length
                  }{' '}
                  (last 7 days)
                </div>
              )}
            {getUnreviewedCount(machine) > 0 && (
              <div className="font-medium text-red-600">
                {getUnreviewedCount(machine)} unreviewed alert
                {getUnreviewedCount(machine) > 1 ? 's' : ''}
              </div>
            )}
            <div className="text-xs text-gray-500">
              <strong>Last seen:</strong>{' '}
              {new Date(machine.data.lastSeen).toLocaleString()}
            </div>
          </div>

          <button
            onClick={handleClick}
            className="mt-2 w-full rounded bg-blue-500 px-2 py-1 text-xs text-white transition-colors hover:bg-blue-600"
          >
            View Details
          </button>
        </div>
      </Popup>
    </Marker>
  );
}

export default function EnhancedReactLeafletMap({
  machines,
  onMarkerClick,
}: MapProps) {
  const center = getMapCenter(machines);
  const zoom = getOptimalZoom(machines);

  // Create activity heat zones for high-activity areas
  const getActivityHeatZones = () => {
    const highActivityMachines = machines.filter((m) => {
      const level = getMachineActivityLevel(m);
      return level === 'critical' || level === 'high';
    });

    return highActivityMachines.map((machine) => ({
      center: [machine.location.lat, machine.location.lng] as [number, number],
      radius: getMachineActivityLevel(machine) === 'critical' ? 1000 : 500,
      color:
        getMachineActivityLevel(machine) === 'critical' ? '#ef4444' : '#f97316',
    }));
  };

  const heatZones = getActivityHeatZones();

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

        {/* Activity Heat Zones Overlay */}
        <LayersControl.Overlay name="Activity Heat Zones">
          <>
            {heatZones.map((zone, index) => (
              <Circle
                key={index}
                center={zone.center}
                radius={zone.radius}
                pathOptions={{
                  fillColor: zone.color,
                  fillOpacity: 0.1,
                  color: zone.color,
                  weight: 2,
                  opacity: 0.4,
                }}
              />
            ))}
          </>
        </LayersControl.Overlay>
      </LayersControl>

      {/* Enhanced Machine Markers with hover popups */}
      {machines.map((machine) => (
        <EnhancedMarker
          key={machine.id}
          machine={machine}
          onMarkerClick={onMarkerClick}
        />
      ))}

      {/* Coverage Areas for Offline Machines (Dark Spots) */}
      {machines
        .filter((m) => m.data.status === 'offline')
        .map((machine) => (
          <Circle
            key={`dark-${machine.id}`}
            center={[machine.location.lat, machine.location.lng]}
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
