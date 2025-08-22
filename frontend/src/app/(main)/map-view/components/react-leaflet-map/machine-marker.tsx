import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { renderToString } from 'react-dom/server';
import { Marker, Popup } from 'react-leaflet';

import { Machine, MachineData } from '@/lib/types/machine';
import { cn, formatEventCount } from '@/lib/utils';

import PopupContent from './popup-content';

const createStatusIcon = (
  machine: Machine,
  machineData: MachineData,
  showName: boolean = false,
) => {
  const isOnline = machineData.is_online;
  const isPulsating = machineData.is_pulsating;
  const severity = machineData.last_event?.severity ?? 0;

  const iconHtml = renderToString(
    <div className="relative">
      {/* Enhanced ripple effect based on severity */}
      {isPulsating && severity > 0 && (
        <>
          {/* Base ripple rings */}
          <div
            className={cn(
              'absolute inset-0 animate-ping rounded-full opacity-75',
              severity === 3
                ? 'bg-red-600'
                : severity === 2
                  ? 'bg-orange-500'
                  : 'bg-blue-500',
            )}
            style={{ animationDuration: '1.5s' }}
          ></div>

          <div
            className={cn(
              'absolute inset-0 animate-ping rounded-full opacity-50',
              severity === 3
                ? 'bg-red-600'
                : severity === 2
                  ? 'bg-orange-500'
                  : 'bg-blue-500',
            )}
            style={{ animationDuration: '1.5s', animationDelay: '0.5s' }}
          ></div>

          <div
            className={cn(
              'absolute inset-0 animate-ping rounded-full opacity-25',
              severity === 3
                ? 'bg-red-600'
                : severity === 2
                  ? 'bg-orange-500'
                  : 'bg-blue-500',
            )}
            style={{ animationDuration: '1.5s', animationDelay: '1s' }}
          ></div>

          {/* Critical event outer ripple */}
          {severity >= 2 && (
            <div
              className={cn(
                'absolute inset-0 rounded-full opacity-30',
                severity === 3
                  ? 'severity-3-ripple bg-red-600'
                  : 'severity-2-ripple bg-orange-500',
              )}
              style={{
                transform: 'scale(1.8)',
                animationDuration: severity === 3 ? '2s' : '1.8s',
              }}
            ></div>
          )}

          {/* Additional critical ripple for weapons */}
          {severity === 3 && (
            <div
              className="severity-3-ripple absolute inset-0 rounded-full bg-red-600 opacity-20"
              style={{
                transform: 'scale(2.2)',
                animationDuration: '2.5s',
                animationDelay: '0.3s',
              }}
            ></div>
          )}
        </>
      )}

      {/* Main machine marker */}
      <div
        className={cn(
          `relative flex h-6 w-6 items-center justify-center rounded-full border-2 shadow-lg transition-all duration-300`,
          isOnline
            ? 'machine-online border-green-300 bg-green-500 text-white shadow-green-500/50'
            : 'machine-offline border-gray-500 bg-gray-700 text-white shadow-gray-500/50',
          isPulsating && severity > 0 ? 'scale-110' : 'scale-100',
          severity > 0 ? 'ring-2 ring-offset-2' : '',
          severity === 3
            ? 'machine-critical ring-red-400'
            : severity === 2
              ? 'ring-orange-400'
              : severity === 1
                ? 'ring-blue-400'
                : '',
        )}
      >
        {/* Severity indicator dot */}
        {severity > 0 && (
          <div
            className={cn(
              'absolute -top-1 -right-1 h-3 w-3 rounded-full border-2 border-white shadow-lg',
              severity === 3
                ? 'bg-red-600'
                : severity === 2
                  ? 'bg-orange-500'
                  : 'bg-blue-500',
            )}
          ></div>
        )}

        <span className="text-xs font-bold">
          {formatEventCount(machineData.event_count)}
        </span>
      </div>

      {/* Machine name label - only show on hover */}
      {showName && (
        <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 transform whitespace-nowrap">
          <div
            className={cn(
              'rounded border px-2 py-1 text-xs font-medium text-white shadow-lg',
              isOnline
                ? 'border-green-500 bg-green-600'
                : 'border-gray-500 bg-gray-600',
            )}
          >
            {machine.name || `Machine ${machine.id}`}
          </div>
        </div>
      )}
    </div>,
  );

  return L.divIcon({
    html: iconHtml,
    iconSize: showName ? [24, 32] : [24, 24], // Original size, larger only when showing name
    popupAnchor: [0, -16],
    className: 'custom-status-marker',
  });
};

interface MachineMarkerProps {
  machine: Machine;
  machineData: MachineData;
}

export default function MachineMarker({
  machine,
  machineData,
}: MachineMarkerProps) {
  const markerRef = useRef<L.Marker>(null);
  const [showName, setShowName] = useState(false);

  // Debug logging
  console.log('📍 [MapView] Machine marker:', {
    machineId: machine.id,
    machineName: machine.name,
    isOnline: machineData.is_online,
    lastLocationTimestamp: machine.last_location?.timestamp,
    isPulsating: machineData.is_pulsating,
    severity: machineData.last_event?.severity,
    eventCount: machineData.event_count,
  });

  // Force icon update when pulsating state changes
  useEffect(() => {
    if (markerRef.current) {
      console.log(
        '🔄 [MapView] Updating icon for machine:',
        machine.id,
        'pulsating:',
        machineData.is_pulsating,
      );
      const newIcon = createStatusIcon(machine, machineData, showName);
      markerRef.current.setIcon(newIcon);
    }
  }, [machineData.is_pulsating, machine, machineData, showName]);

  const handleClick = () => {
    if (markerRef.current) {
      markerRef.current.openPopup();
    }
  };

  const handleMouseEnter = () => {
    setShowName(true);
  };

  const handleMouseLeave = () => {
    setShowName(false);
  };

  return (
    <Marker
      ref={markerRef}
      icon={createStatusIcon(machine, machineData, showName)}
      position={[
        machine?.last_location?.lat ?? 0,
        machine?.last_location?.long ?? 0,
      ]}
      eventHandlers={{
        click: handleClick,
        mouseover: handleMouseEnter,
        mouseout: handleMouseLeave,
      }}
    >
      <Popup className="custom-popup" closeButton={false}>
        <PopupContent
          machine={machine}
          machineData={machineData}
          isOnline={machineData.is_online}
        />
      </Popup>
    </Marker>
  );
}
