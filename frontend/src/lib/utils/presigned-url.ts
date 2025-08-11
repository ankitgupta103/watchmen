import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';

interface PresignedUrlResponse {
  success: boolean;
  url?: string;
  error?: string;
}

export async function getPresignedUrl(
  filename: string,
  token: string | null,
  bucket: string = 'vyomos'
): Promise<string | null> {
  if (!token || !filename) {
    console.warn('[PresignedURL] Missing token or filename:', { token: !!token, filename });
    return null;
  }

  try {
    console.log('[PresignedURL] Requesting presigned URL for:', filename);
    
    // Use GET request with query parameters
    const queryParams = new URLSearchParams({
      bucket,
      filename,
    });

    const response = await fetcherClient<PresignedUrlResponse>(
      `${API_BASE_URL}/s3-presigned-url/?${queryParams.toString()}`,
      token,
      {
        method: 'GET',
      }
    );

    if (response?.success && response.url) {
      console.log('[PresignedURL] Successfully received presigned URL for:', filename);
      return response.url;
    } else {
      console.error('[PresignedURL] Failed to get presigned URL for:', filename, response?.error);
      return null;
    }
  } catch (error) {
    console.error('[PresignedURL] Error requesting presigned URL for:', filename, error);
    return null;
  }
}

export async function getMultiplePresignedUrls(
  filenames: string[],
  token: string | null,
  bucket: string = 'vyomos'
): Promise<Record<string, string>> {
  if (!token || !filenames.length) {
    return {};
  }

  console.log('[PresignedURL] Requesting multiple presigned URLs:', filenames.length);

  const urlPromises = filenames.map(async (filename) => {
    const url = await getPresignedUrl(filename, token, bucket);
    return { filename, url };
  });

  const results = await Promise.allSettled(urlPromises);
  
  const urlMap: Record<string, string> = {};
  results.forEach((result, index) => {
    if (result.status === 'fulfilled' && result.value.url) {
      urlMap[result.value.filename] = result.value.url;
    } else {
      console.warn('[PresignedURL] Failed to get URL for:', filenames[index]);
    }
  });

  console.log('[PresignedURL] Successfully retrieved', Object.keys(urlMap).length, 'URLs');
  return urlMap;
}