import { useEffect, useState } from 'react';
import useToken from '@/hooks/use-token';
import { Activity, AlertTriangle, Camera, Clock, Loader2 } from 'lucide-react';
import Image from 'next/image';

import { Badge } from '@/components/ui/badge';

import { Machine, MachineData } from '@/lib/types/machine';
import { cn } from '@/lib/utils';
import {
  getMultiplePresignedUrls,
  getPresignedUrl,
} from '@/lib/utils/presigned-url';
import { getSeverityLabel } from '@/lib/utils/severity';

interface PopupContentProps {
  machine: Machine;
  machineData: MachineData;
  isOnline: boolean;
}

export default function PopupContent({
  machine,
  machineData,
  isOnline,
}: PopupContentProps) {
  const { token } = useToken();
  const [imageUrls, setImageUrls] = useState<{
    full: string | null;
    cropped: Record<string, string>;
  }>({ full: null, cropped: {} });
  const [isLoading, setIsLoading] = useState(false);

  const { last_event, event_count } = machineData;

  useEffect(() => {
    const fetchImages = async () => {
      if (
        !last_event ||
        (!last_event.original_image_path && !last_event.cropped_images?.length)
      ) {
        return;
      }

      setIsLoading(true);

      let fullUrl: string | null = null;
      let croppedUrls: Record<string, string> = {};

      // Prefer annotated_image_path over original_image_path, similar to dashboard
      const imagePath = ('annotated_image_path' in last_event ? (last_event as { annotated_image_path: string }).annotated_image_path : null) || last_event.original_image_path;
      if (imagePath) {
        fullUrl = await getPresignedUrl(imagePath, token);
      }

      if (last_event.cropped_images && last_event.cropped_images.length > 0) {
        const filenames = last_event.cropped_images.map(
          (img) => img.image_file_path,
        );
        croppedUrls = await getMultiplePresignedUrls(filenames, token);
      }

      setImageUrls({ full: fullUrl, cropped: croppedUrls });
      setIsLoading(false);
    };

    fetchImages();
  }, [last_event, token]);

  const severityInfo = last_event
    ? getSeverityLabel(last_event.severity)
    : null;

  return (
    <div className="max-h-96 w-fit overflow-y-auto p-4">
      {/* Header */}
      <div className="mb-3 border-b pb-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h3 className="text-lg font-bold text-gray-900">
            {machine.name || `Machine ${machine.id}`}
          </h3>
          <Badge
            variant={isOnline ? 'default' : 'destructive'}
            className={cn(
              'text-xs font-medium',
              isOnline
                ? 'bg-green-500 hover:bg-green-600'
                : 'bg-red-500 hover:bg-red-600',
            )}
          >
            {isOnline ? '🟢 Online' : '🔴 Offline'}
          </Badge>
        </div>

        <div className="flex items-center gap-4 text-xs text-gray-600">
          <div className="flex items-center gap-1">
            <Activity className="h-3 w-3" />
            ID: {machine.id}
          </div>
          <div className="flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            {event_count} Events
          </div>
        </div>
      </div>

      {/* Last Event Section */}
      {last_event && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-gray-800">
              Latest Event
            </h4>
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3 text-gray-500" />
              <span className="text-xs text-gray-500">
                {last_event.timestamp.toLocaleTimeString()}
              </span>
            </div>
          </div>

          {/* Severity Badge */}
          {severityInfo && (
            <div className="flex items-center gap-2">
              <Badge
                className={cn('text-xs font-medium', severityInfo.className)}
              >
                {severityInfo.label}
              </Badge>
            </div>
          )}

          {/* Event Description */}
          <div className="rounded-lg bg-gray-50 p-3">
            <p className="text-sm text-gray-700">
              {last_event.cropped_images?.map(img => img.class_name).join(', ') || 'Event detected'}
            </p>
          </div>

          {/* Images Section */}
          {isLoading && (
            <div className="flex items-center justify-center p-6">
              <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
              <span className="ml-2 text-sm text-gray-600">
                Loading Images...
              </span>
            </div>
          )}

          {!isLoading &&
            !imageUrls.full &&
            Object.keys(imageUrls.cropped).length === 0 && (
              <div className="py-4 text-center text-gray-500">
                <Camera className="mx-auto mb-2 h-8 w-8 text-gray-400" />
                <p className="text-sm">No images for this event</p>
              </div>
            )}

          {/* Full Scene Image */}
          {imageUrls.full && (
            <div className="space-y-2">
              <p className="text-xs font-medium tracking-wide text-gray-600 uppercase">
                Full Scene
              </p>
              <div className="relative h-48 w-full overflow-hidden rounded-lg border bg-gray-100">
                <Image
                  src={imageUrls.full}
                  alt="Full scene"
                  fill
                  className="object-cover"
                />
              </div>
            </div>
          )}

          {/* Cropped Detections */}
          {last_event.cropped_images &&
            last_event.cropped_images.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium tracking-wide text-gray-600 uppercase">
                  Detected Objects ({last_event.cropped_images.length})
                </p>
                <div className="grid grid-cols-2 gap-3">
                  {last_event.cropped_images.map((img, index) => {
                    const imageUrl = imageUrls.cropped[img.image_file_path];
                    return (
                      <div key={index} className="space-y-2">
                        <div className="aspect-square overflow-hidden rounded-lg border bg-gray-100">
                          {imageUrl ? (
                            <Image
                              src={imageUrl}
                              alt={img.class_name}
                              width={120}
                              height={120}
                              className="h-full w-full object-cover"
                            />
                          ) : (
                            <div className="flex h-full w-full items-center justify-center text-gray-400">
                              <Camera size={32} />
                            </div>
                          )}
                        </div>
                        <div className="text-center">
                          <Badge
                            variant="outline"
                            className="text-xs font-medium"
                          >
                            {img.class_name}
                          </Badge>
                          <div className="mt-1 text-xs text-gray-500">
                            Confidence: {Math.round(img.confidence * 100)}%
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
        </div>
      )}

      {/* No Events Message */}
      {!last_event && (
        <div className="py-8 text-center text-gray-500">
          <Activity className="mx-auto mb-3 h-12 w-12 text-gray-400" />
          <p className="text-sm">No events recorded yet</p>
          <p className="mt-1 text-xs text-gray-400">
            This machine is monitoring for activity
          </p>
        </div>
      )}
    </div>
  );
}
