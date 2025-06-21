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
import { Machine, SimpleMachineData } from '@/lib/types/machine';
import {
  calculateMapCenter,
  calculateOptimalZoom,
  cn,
  formatEventCount,
  getMarkerColors,
  getStatusColor,
  getStatusText,
  isMachineOnline,
} from '@/lib/utils';

interface MapProps {
  machines: Machine[];
  onMarkerClick: (machine: Machine) => void;
  getMachineData: (machineId: number) => SimpleMachineData;
}

/**
 * Creates enhanced custom icon with online/offline status and pulsating animation
 */
const createStatusIcon = (machine: Machine, machineData: SimpleMachineData) => {
  const isOnline = isMachineOnline(machine);
  const isPulsating = machineData.is_pulsating;
  const isCritical = machineData.is_critical;
  const eventCount = machineData.event_count;

  const colors = getMarkerColors(isCritical, eventCount);

  const iconHtml = renderToString(
    <div className="relative">
      {/* Pulsating wave animation for machines with recent events */}
      {isPulsating && (
        <>
          <div
            className={`absolute inset-0 rounded-full ${colors.bg} animate-ping opacity-75 duration-100`}
          ></div>
          <div
            className={`absolute inset-0 rounded-full ${colors.bg} animate-ping opacity-50 duration-500`}
          ></div>
          <div
            className={`absolute inset-0 rounded-full ${colors.bg} animate-ping opacity-25 duration-1000`}
          ></div>
        </>
      )}

      {/* Main marker */}
      <div
        className={cn(
          `relative flex h-5 w-5 items-center justify-center rounded-full border-1`,
          isOnline ? 'bg-green-500 text-white' : 'bg-gray-700 text-white',
        )}
      >
        <span className="text-xs font-bold">
          {formatEventCount(eventCount)}
        </span>
      </div>
    </div>,
  );

  return L.divIcon({
    html: iconHtml,
    iconSize: [24, 24],
    popupAnchor: [0, -16],
    className: 'custom-status-marker',
  });
};

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

  const isOnline = isMachineOnline(machine);

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

  return (
    <Marker
      ref={markerRef}
      icon={createStatusIcon(machine, machineData)}
      position={[
        machine?.last_location?.lat ?? 12.9716,
        machine?.last_location?.long ?? 77.5946,
      ]}
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
        <PopupContent
          machine={machine}
          machineData={machineData}
          isOnline={isOnline}
        />
      </Popup>
    </Marker>
  );
}

/**
 * Popup content component for better organization
 */
interface PopupContentProps {
  machine: Machine;
  machineData: SimpleMachineData;
  isOnline: boolean;
}

function PopupContent({ machine, machineData, isOnline }: PopupContentProps) {
  return (
    <>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">{machine.name.toUpperCase()}</h3>
        <Badge
          variant={isOnline ? 'default' : 'destructive'}
          className="text-xs"
        >
          {isOnline ? 'Online' : 'Offline'}
        </Badge>
      </div>

      <div className="space-y-1 text-xs">
        <div>
          <strong>Machine ID:</strong> {machine.id}
        </div>

        {/* Status information */}
        <div className={cn('font-medium', getStatusColor(isOnline))}>
          <strong>Status:</strong>{' '}
          {getStatusText(isOnline, machineData.event_count)}
        </div>

        {/* Recent event activity indicator */}
        {machineData.is_pulsating && (
          <div className="mt-1 border-t pt-1 text-xs text-orange-600">
            <strong>🔔 Recent Event Activity</strong>
          </div>
        )}

        {/* Last event info */}
        {machineData.last_event && (
          <div className="mt-1 border-t pt-1 text-xs text-blue-600">
            <strong>Last Event:</strong> {machineData.last_event.eventstr}
            <br />
            <span className="text-gray-500">
              {new Date(machineData.last_event.timestamp).toLocaleTimeString()}
            </span>
          </div>
        )}

        <div className="mt-1 border-t pt-1 text-xs text-gray-500">
          <strong>Location:</strong> {machine?.last_location?.lat ?? '0.0000'},{' '}
          {machine?.last_location?.long ?? '0.0000'}
        </div>

        <div className="text-xs text-gray-400">Click to view details</div>
      </div>
    </>
  );
}

/**
 * Main map component with optimized center and zoom calculation
 */
export default function SimplifiedReactLeafletMap({
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
