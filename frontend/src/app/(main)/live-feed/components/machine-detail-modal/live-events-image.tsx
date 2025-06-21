'use client';

import { memo, useEffect, useState } from 'react';
import { ImageIcon, Loader2, RefreshCw } from 'lucide-react';
import Image from 'next/image';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';

interface LiveEventImageProps {
  token: string | null;
  image_c_key?: string;
  image_f_key?: string;
  onImageClick: (url: string) => void;
  eventId: string;
}

interface ImageUrlResponse {
  croppedImageUrl?: string;
  fullImageUrl?: string;
}

const fetchEventImages = async (
  token: string,
  imageKeys: { image_c_key: string; image_f_key: string },
) => {
  try {
    const data = await fetcherClient<{
      success: boolean;
      cropped_image_url?: string;
      full_image_url?: string;
      error?: string;
    }>(`${API_BASE_URL}/event-images/`, token, {
      method: 'POST',
      body: imageKeys,
    });

    if (data?.success) {
      return {
        croppedImageUrl: data.cropped_image_url,
        fullImageUrl: data.full_image_url,
      };
    }
    return null;
  } catch (error) {
    console.error('Error fetching images:', error);
    throw error;
  }
};

const LiveEventImage = memo(
  ({
    token,
    image_c_key,
    image_f_key,
    onImageClick,
    eventId,
  }: LiveEventImageProps) => {
    const [imageUrls, setImageUrls] = useState<ImageUrlResponse | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isPolling, setIsPolling] = useState(false);

    useEffect(() => {
      if (imageUrls || !token || !image_c_key || !image_f_key) {
        return;
      }

      let intervalId: NodeJS.Timeout | null = null;

      const attemptFetch = async () => {
        setError(null);
        try {
          const urls = await fetchEventImages(token, {
            image_c_key,
            image_f_key,
          });
          if (urls?.croppedImageUrl || urls?.fullImageUrl) {
            setImageUrls(urls);
            setIsPolling(false);
            setIsLoading(false);
            // On success, immediately clear the interval
            if (intervalId) {
              clearInterval(intervalId);
            }
          } else {
            setIsPolling(true);
          }
        } catch (err) {
          setError('Network error. Retrying...');
          setIsPolling(true);
          console.error('Error fetching images for event:', eventId, err);
        }
      };

      setIsLoading(true);
      attemptFetch().finally(() => {
        setIsLoading(false);
      });

      intervalId = setInterval(attemptFetch, 5000);

      return () => {
        if (intervalId) {
          clearInterval(intervalId);
        }
      };
    }, [token, image_c_key, image_f_key, eventId, imageUrls]);

    const hasImageKeys = image_c_key && image_f_key;

    if (!hasImageKeys) {
      return (
        <div className="flex h-48 flex-col items-center justify-center rounded border bg-gray-50 text-center text-xs text-gray-500">
          <ImageIcon className="mb-1 h-6 w-6 text-gray-400" />
          No Image Data
        </div>
      );
    }

    if (isLoading) {
      return (
        <div className="flex h-48 items-center justify-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading images...
        </div>
      );
    }

    if (isPolling) {
      return (
        <div className="flex h-48 flex-col items-center justify-center gap-2 rounded border bg-blue-50/50 p-4 text-center text-sm text-blue-700">
          <div className="flex items-center gap-2">
            <RefreshCw className="h-4 w-4 animate-spin" />
            <span>Image is processing...</span>
          </div>
          {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
          {!error && (
            <p className="mt-1 text-xs text-blue-500">
              Will retry automatically.
            </p>
          )}
        </div>
      );
    }

    if (imageUrls?.croppedImageUrl || imageUrls?.fullImageUrl) {
      return (
        <div className="flex flex-col items-center justify-center gap-2 lg:flex-row">
          {imageUrls.croppedImageUrl && (
            <div className="w-full space-y-1">
              <Image
                src={imageUrls.croppedImageUrl}
                alt="Cropped live event"
                width={300}
                height={400}
                className="h-80 w-fit max-w-full cursor-pointer rounded-lg border bg-slate-100 object-contain transition-transform hover:scale-105"
                onClick={() => onImageClick(imageUrls.croppedImageUrl!)}
              />
            </div>
          )}
          {imageUrls.fullImageUrl && (
            <div className="w-full space-y-1">
              <Image
                src={imageUrls.fullImageUrl}
                alt="Full live event"
                width={500}
                height={400}
                className="h-80 w-fit max-w-full cursor-pointer rounded-lg border bg-slate-100 object-contain transition-transform hover:scale-105"
                onClick={() => onImageClick(imageUrls.fullImageUrl!)}
              />
            </div>
          )}
        </div>
      );
    }

    return (
      <div className="flex h-48 flex-col items-center justify-center rounded border bg-gray-50 text-center text-xs text-gray-500">
        <ImageIcon className="mb-1 h-6 w-6 text-gray-400" />
        Preparing image...
      </div>
    );
  },
);

LiveEventImage.displayName = 'LiveEventImage';

export default LiveEventImage;
