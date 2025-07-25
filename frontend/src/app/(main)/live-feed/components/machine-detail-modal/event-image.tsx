'use client';

import { useEffect, useRef, useState } from 'react';
import { ImageIcon, Loader2 } from 'lucide-react';
import Image from 'next/image';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';

interface EventImageProps {
  token: string | null;
  image_c_key?: string;
  image_f_key?: string;
  onImageClick: (url: string) => void;
}

interface ImageUrlResponse {
  croppedImageUrl?: string;
  fullImageUrl?: string;
}

const fetchEventImages = async (
  token: string,
  imageKeys: { image_c_key: string; image_f_key: string },
  signal?: AbortSignal,
  retries = 2,
  backoff = 2000,
): Promise<ImageUrlResponse | null> => {
  try {
    // Check if already aborted
    if (signal?.aborted) {
      return null;
    }

    const data = await fetcherClient<{
      success: boolean;
      cropped_image_url?: string;
      full_image_url?: string;
      error?: string;
    }>(`${API_BASE_URL}/event-images/`, token, {
      method: 'POST',
      body: imageKeys,
      signal, // Pass the abort signal to the fetch request
    });

    if (data?.success) {
      return {
        croppedImageUrl: data.cropped_image_url,
        fullImageUrl: data.full_image_url,
      };
    }
    throw new Error(data?.error || 'Failed to fetch images');
  } catch (error) {
    // Don't retry if the request was aborted
    if (error instanceof Error && error.name === 'AbortError') {
      return null;
    }

    if (retries > 0 && !signal?.aborted) {
      await new Promise((res) => setTimeout(res, backoff));
      return fetchEventImages(
        token,
        imageKeys,
        signal,
        retries - 1,
        backoff * 2,
      );
    }
    console.error('Error fetching images:', error);
    return null;
  }
};

const EventImage = ({
  token,
  image_c_key,
  image_f_key,
  onImageClick,
}: EventImageProps) => {
  const [imageUrls, setImageUrls] = useState<ImageUrlResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchImages = async () => {
      if (!token || !image_c_key || !image_f_key) {
        return;
      }

      // Cancel any ongoing request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller for this request
      abortControllerRef.current = new AbortController();
      const signal = abortControllerRef.current.signal;

      setIsLoading(true);
      setError(null);

      const urls = await fetchEventImages(
        token,
        { image_c_key, image_f_key },
        signal,
      );

      // Only update state if request wasn't aborted
      if (!signal.aborted && isMounted) {
        if (urls && (urls.croppedImageUrl || urls.fullImageUrl)) {
          setImageUrls(urls);
          setIsLoading(false);
        } else {
          setImageUrls(null);
          setIsLoading(false);
        }
      }
    };

    fetchImages();

    // Cleanup function to abort request on unmount or dependency change
    return () => {
      isMounted = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [token, image_c_key, image_f_key]);

  const hasImageKeys = image_c_key && image_f_key;

  if (!hasImageKeys) {
    return (
      <div className="flex h-32 flex-col items-center justify-center rounded border bg-gray-50 text-center text-xs text-gray-500">
        <ImageIcon className="mb-1 h-6 w-6 text-gray-400" />
        No Image Data
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center rounded border bg-gray-50">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-32 flex-col items-center justify-center rounded border bg-red-50/50 text-center text-xs text-red-600">
        <ImageIcon className="mb-1 h-6 w-6" />
        {error}
      </div>
    );
  }

  if (imageUrls?.croppedImageUrl || imageUrls?.fullImageUrl) {
    return (
      <div className="grid grid-cols-2 gap-2">
        {imageUrls.croppedImageUrl && (
          <Image
            src={imageUrls.croppedImageUrl}
            alt="Cropped historical"
            width={150}
            height={150}
            className="h-24 w-full cursor-pointer rounded border object-cover"
            onClick={() => onImageClick(imageUrls.croppedImageUrl!)}
          />
        )}
        {imageUrls.fullImageUrl && (
          <Image
            src={imageUrls.fullImageUrl}
            alt="Full historical"
            width={150}
            height={150}
            className="h-24 w-full cursor-pointer rounded border object-cover"
            onClick={() => onImageClick(imageUrls.fullImageUrl!)}
          />
        )}
      </div>
    );
  }

  return (
    <div className="flex h-32 flex-col items-center justify-center rounded border bg-gray-50 text-center text-xs text-gray-500">
      <ImageIcon className="mb-1 h-6 w-6 text-gray-400" />
      No Image Data
    </div>
  );
};

export default EventImage;
