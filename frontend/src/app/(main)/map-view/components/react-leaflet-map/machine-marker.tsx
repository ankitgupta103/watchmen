import { useRef } from 'react';
import L from 'leaflet';
import { renderToString } from 'react-dom/server';
import { Marker, Popup } from 'react-leaflet';

import { Machine, MachineData } from '@/lib/types/machine';
import {
  cn,
  formatEventCount,
  getMarkerColors,
  isMachineOnline,
} from '@/lib/utils';

import PopupContent from './popup-content';

const createStatusIcon = (machine: Machine, machineData: MachineData) => {
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

interface MachineMarker {
  machine: Machine;
  machineData: MachineData;
  onMarkerClick: (machine: Machine) => void;
}

export default function MachineMarker({
  machine,
  machineData,
  onMarkerClick,
}: MachineMarker) {
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
