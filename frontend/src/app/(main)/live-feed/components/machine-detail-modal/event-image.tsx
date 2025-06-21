'use client';

import { useEffect, useState } from 'react';
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
  retries = 1000,
  backoff = 2000,
): Promise<ImageUrlResponse | null> => {
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
    throw new Error(data?.error || 'Failed to fetch images');
  } catch (error) {
    if (retries > 0) {
      await new Promise(res => setTimeout(res, backoff));
      return fetchEventImages(token, imageKeys, retries - 1, backoff * 2);
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

  useEffect(() => {
    const fetchImages = async () => {
      if (!token || !image_c_key || !image_f_key) {
        return;
      }
      setIsLoading(true);
      setError(null);
      const urls = await fetchEventImages(token, { image_c_key, image_f_key });
      if (urls) {
        setImageUrls(urls);
      } else {
        setError('Failed to load images.');
      }
      setIsLoading(false);
    };

    fetchImages();
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
    <div className="flex h-32 flex-col items-center justify-center rounded border bg-blue-50/50 text-center text-xs text-blue-600">
      <ImageIcon className="mb-1 h-6 w-6" />
      Images Available
    </div>
  );
};

export default EventImage;
