import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

import { MachineEvent } from './types/activity';
import { Machine, MarkerColors } from './types/machine';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function toTitleCase(str: string) {
  return str.replace(/\b\w/g, (char) => char.toUpperCase());
}

export const formatBufferSize = (
  bytes: number,
  decimals = 2,
  useIEC = false,
) => {
  if (typeof bytes !== 'number' || isNaN(Number(bytes))) return '-';
  if (bytes === 0) return '0 Bytes';
  const k = useIEC ? 1024 : 1000;
  const sizes = useIEC
    ? ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
    : ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  const i = Math.floor(Math.log(Number(bytes)) / Math.log(k));

  const formattedSize = parseFloat(
    (Number(bytes) / Math.pow(k, i)).toFixed(decimals),
  );
  return `${formattedSize} ${sizes[i]}`;
};

// Helper to format duration in ms to hours/minutes
export const formatDuration = (ms: number) => {
  if (!ms || isNaN(ms)) return '-';
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else {
    return `${minutes}min`;
  }
};

export const durationMs = (start: string, end: string) => {
  return Math.abs(new Date(start).getTime() - new Date(end).getTime());
};

// Constants
export const ONE_HOUR_MS = 1000 * 60 * 60;
export const MAX_EVENTS_PER_MACHINE = 3;
export const MAX_EVENT_COUNT_FOR_COLOR = 20;
export const PULSATING_DURATION_MS = 30000;

/**
 * Determines if a machine is online based on its last location timestamp
 */
export const isMachineOnline = (machine: Machine): boolean => {
  const lastSeen = machine.last_location?.timestamp
    ? new Date(machine.last_location.timestamp)
    : null;
  const oneHourAgo = new Date(Date.now() - ONE_HOUR_MS);
  return !!lastSeen && lastSeen > oneHourAgo;
};

/**
 * Checks if any events are critical (severity level 3)
 */
export const hasCriticalEvents = (events: MachineEvent[]): boolean => {
  return events.some((event) => event.event_severity === '3');
};

/**
 * Gets marker colors based on event severity and count
 */
export const getMarkerColors = (
  isCritical: boolean,
  eventCount: number,
): MarkerColors => {
  if (isCritical) {
    return {
      bg: 'bg-red-500',
      border: 'border-red-600',
      text: 'text-red-100',
    };
  }

  if (eventCount > 10) {
    return {
      bg: 'bg-orange-500',
      border: 'border-orange-600',
      text: 'text-orange-100',
    };
  }

  return {
    bg: 'bg-yellow-500',
    border: 'border-yellow-600',
    text: 'text-yellow-100',
  };
};

/**
 * Generates a unique event ID
 */
export const generateEventId = (): string => {
  return `event-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Formats event count for display (caps at 99+)
 */
export const formatEventCount = (count: number): string => {
  return count > 99 ? '99+' : count.toString();
};

/**
 * Gets status text for machine based on online status and event count
 */
export const getStatusText = (
  isOnline: boolean,
  eventCount: number,
): string => {
  if (isOnline) {
    if (eventCount > 0) {
      return `Online - ${eventCount} recent events`;
    }
    return 'Online - No recent events';
  }
  return 'Offline';
};

/**
 * Gets status color CSS class
 */
export const getStatusColor = (isOnline: boolean): string => {
  return isOnline ? 'text-green-600' : 'text-gray-600';
};

/**
 * Calculates map center from array of machines
 */
export const calculateMapCenter = (machines: Machine[]): [number, number] => {
  const DEFAULT_LAT = 12.9716; // Bangalore
  const DEFAULT_LNG = 77.5946;

  if (machines.length === 0) return [DEFAULT_LAT, DEFAULT_LNG];

  const bounds = machines.reduce(
    (acc, machine) => ({
      minLat: Math.min(acc.minLat, machine?.last_location?.lat ?? DEFAULT_LAT),
      maxLat: Math.max(acc.maxLat, machine?.last_location?.lat ?? DEFAULT_LAT),
      minLng: Math.min(acc.minLng, machine?.last_location?.long ?? DEFAULT_LNG),
      maxLng: Math.max(acc.maxLng, machine?.last_location?.long ?? DEFAULT_LNG),
    }),
    {
      minLat: machines[0]?.last_location?.lat ?? DEFAULT_LAT,
      maxLat: machines[0]?.last_location?.lat ?? DEFAULT_LAT,
      minLng: machines[0]?.last_location?.long ?? DEFAULT_LNG,
      maxLng: machines[0]?.last_location?.long ?? DEFAULT_LNG,
    },
  );

  return [
    (bounds.minLat + bounds.maxLat) / 2,
    (bounds.minLng + bounds.maxLng) / 2,
  ];
};

/**
 * Calculates optimal zoom level based on machine distribution
 */
export const calculateOptimalZoom = (machines: Machine[]): number => {
  const DEFAULT_LAT = 12.9716;
  const DEFAULT_LNG = 77.5946;

  if (machines.length <= 1) return 12;

  const bounds = machines.reduce(
    (acc, machine) => ({
      minLat: Math.min(acc.minLat, machine?.last_location?.lat ?? DEFAULT_LAT),
      maxLat: Math.max(acc.maxLat, machine?.last_location?.lat ?? DEFAULT_LAT),
      minLng: Math.min(acc.minLng, machine?.last_location?.long ?? DEFAULT_LNG),
      maxLng: Math.max(acc.maxLng, machine?.last_location?.long ?? DEFAULT_LNG),
    }),
    {
      minLat: machines[0]?.last_location?.lat ?? DEFAULT_LAT,
      maxLat: machines[0]?.last_location?.lat ?? DEFAULT_LAT,
      minLng: machines[0]?.last_location?.long ?? DEFAULT_LNG,
      maxLng: machines[0]?.last_location?.long ?? DEFAULT_LNG,
    },
  );

  const latDiff = bounds.maxLat - bounds.minLat;
  const lngDiff = bounds.maxLng - bounds.minLng;
  const maxDiff = Math.max(latDiff, lngDiff);

  if (maxDiff > 10) return 4;
  if (maxDiff > 5) return 6;
  if (maxDiff > 1) return 8;
  if (maxDiff > 0.5) return 10;
  if (maxDiff > 0.1) return 12;
  return 14;
};

/**
 * Counts machines by online status
 */
export const countMachinesByStatus = (machines: Machine[]) => {
  const online = machines.filter(isMachineOnline).length;
  const offline = machines.length - online;
  return { online, offline };
};
