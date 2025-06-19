import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

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
