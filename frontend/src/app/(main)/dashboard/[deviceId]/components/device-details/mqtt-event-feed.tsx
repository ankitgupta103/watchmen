'use client';

import React, { useEffect, useState } from 'react';
import Image from 'next/image';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { MQTTEvent } from '@/lib/types/machine';
import { calculateSeverity, getSeverityLabel } from '@/lib/utils/severity';
import { cn } from '@/lib/utils';
import { getPresignedUrl, getMultiplePresignedUrls } from '@/lib/utils/presigned-url';
import useToken from '@/hooks/use-token';

interface MQTTEventFeedProps {
  events: MQTTEvent[];
  className?: string;
}

interface EventItemProps {
  event: MQTTEvent;
}

const EventItem: React.FC<EventItemProps> = ({ event }) => {
  const { token } = useToken();
  const [fullImageUrl, setFullImageUrl] = useState<string | null>(null);
  const [croppedImageUrls, setCroppedImageUrls] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const severity = event.severity || calculateSeverity(event.cropped_images);
  const severityInfo = getSeverityLabel(severity);

  // Fetch presigned URLs when component mounts
  useEffect(() => {
    const fetchImages = async () => {
      if (!token || loading) return;
      
      setLoading(true);
      
      try {
        setError(null);
        
        // Fetch full image URL
        if (event.full_image_url) {
          setFullImageUrl(event.full_image_url);
        } else if (event.original_image_path) {
          const url = await getPresignedUrl(event.original_image_path, token);
          setFullImageUrl(url);
        }
        
        // Fetch cropped image URLs
        if (event.cropped_images && event.cropped_images.length > 0) {
          const filenames = event.cropped_images.map(img => img.image_file_path);
          const urls = await getMultiplePresignedUrls(filenames, token);
          setCroppedImageUrls(urls);
          
          if (Object.keys(urls).length === 0) {
            setError('Failed to load images');
          }
        }
      } catch (err) {
        console.error('Error fetching presigned URLs:', err);
        setError('Failed to load images');
      } finally {
        setLoading(false);
      }
    };
    
    fetchImages();
  }, [token, event.full_image_url, event.original_image_path, event.cropped_images, loading]);
  
  const formatTimestamp = (timestamp: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - new Date(timestamp).getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return new Date(timestamp).toLocaleDateString();
  };

  return (
    <Card className="mb-4 shadow-sm hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-blue-600 font-semibold text-sm">WM</span>
            </div>
            <div>
              <p className="font-medium text-sm">Watchmen System</p>
              <p className="text-xs text-gray-500">
                {formatTimestamp(event.timestamp)}
              </p>
            </div>
          </div>
          <Badge 
            variant="outline" 
            className={cn('text-xs', severityInfo.className)}
          >
            {severityInfo.label}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="mb-3">
          <p className="text-sm text-gray-700">
            Detection Alert: {event.cropped_images.length} object(s) detected
          </p>
          <div className="mt-2 flex flex-wrap gap-1">
            {event.cropped_images.map((img, index) => (
              <Badge key={index} variant="secondary" className="text-xs">
                {img.class_name} ({Math.round(img.confidence * 100)}%)
              </Badge>
            ))}
          </div>
        </div>
        
        {/* Main image or detection placeholder */}
        {loading ? (
          <div className="w-full h-64 bg-gray-100 rounded-lg mb-3 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
              <p className="text-gray-500 text-sm">Loading images...</p>
            </div>
          </div>
        ) : fullImageUrl ? (
          <div className="relative w-full h-64 bg-gray-100 rounded-lg overflow-hidden mb-3">
            <Image
              src={fullImageUrl}
              alt="Detection event"
              fill
              className="object-cover"
            />
            {/* Overlay showing total detections */}
            <div className="absolute top-3 right-3 bg-black/70 text-white px-2 py-1 rounded-md text-xs">
              {event.cropped_images.length} detection{event.cropped_images.length !== 1 ? 's' : ''}
            </div>
          </div>
        ) : error ? (
          <div className="w-full h-64 bg-red-50 border border-red-200 rounded-lg mb-3 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 bg-red-200 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-2xl">⚠️</span>
              </div>
              <p className="text-red-600 font-medium">Failed to Load Images</p>
              <p className="text-red-500 text-sm">{event.cropped_images.length} objects detected</p>
            </div>
          </div>
        ) : (
          <div className="w-full h-64 bg-gradient-to-br from-blue-50 to-indigo-100 rounded-lg mb-3 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-200 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-2xl">📷</span>
              </div>
              <p className="text-gray-600 font-medium">Security Detection</p>
              <p className="text-gray-500 text-sm">{event.cropped_images.length} objects detected</p>
            </div>
          </div>
        )}
        
        {/* Detection grid - Facebook-style photo layout */}
        {event.cropped_images.length > 0 && (
          <div className="mb-3">
            <div className={cn(
              "grid gap-2",
              event.cropped_images.length === 1 ? "grid-cols-1" :
              event.cropped_images.length === 2 ? "grid-cols-2" :
              event.cropped_images.length === 3 ? "grid-cols-3" :
              event.cropped_images.length === 4 ? "grid-cols-2" :
              "grid-cols-3"
            )}>
              {event.cropped_images.slice(0, 5).map((img, index) => {
                const imageUrl = croppedImageUrls[img.image_file_path];
                
                return (
                  <div 
                    key={index} 
                    className={cn(
                      "relative bg-gray-100 rounded-lg overflow-hidden border-2 border-transparent hover:border-blue-300 transition-colors",
                      // Special styling for different layouts
                      event.cropped_images.length === 4 && index === 3 ? "col-span-2" : "",
                      event.cropped_images.length >= 5 && index === 0 ? "col-span-2 row-span-2" : "",
                      "aspect-square"
                    )}
                  >
                    {imageUrl ? (
                      <>
                        <Image
                          src={imageUrl}
                          alt={`${img.class_name} detection`}
                          fill
                          className="object-cover"
                        />
                        {/* Overlay with class name and confidence */}
                        <div className="absolute inset-0 bg-black/40 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center">
                          <div className="text-center text-white">
                            <div className="text-xs font-medium capitalize">
                              {img.class_name}
                            </div>
                            <div className="text-xs">
                              {Math.round(img.confidence * 100)}%
                            </div>
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="absolute inset-0 flex flex-col items-center justify-center p-2">
                        <div className="text-center">
                          <div className="text-3xl mb-2">
                            {img.class_name === 'person' ? '👤' :
                             img.class_name === 'gun' ? '🔫' :
                             img.class_name === 'backpack' ? '🎒' :
                             img.class_name === 'car' ? '🚗' :
                             img.class_name === 'knife' ? '🔪' : '📦'}
                          </div>
                          <div className="text-xs font-medium text-gray-700 capitalize">
                            {img.class_name}
                          </div>
                          <div className="text-xs text-gray-500">
                            {Math.round(img.confidence * 100)}%
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Confidence indicator */}
                    <div className="absolute top-2 right-2">
                      <div className={cn(
                        "w-3 h-3 rounded-full border-2 border-white",
                        img.confidence >= 0.8 ? "bg-green-400" :
                        img.confidence >= 0.6 ? "bg-yellow-400" : "bg-red-400"
                      )} />
                    </div>
                    
                    {/* Class label */}
                    <div className="absolute bottom-2 left-2">
                      <Badge variant="secondary" className="text-xs">
                        {img.class_name}
                      </Badge>
                    </div>
                  </div>
                );
              })}
              
              {/* Show more indicator */}
              {event.cropped_images.length > 5 && (
                <div className="relative aspect-square bg-gray-200 rounded-lg flex items-center justify-center">
                  <div className="text-center text-gray-600">
                    <div className="text-lg font-bold">+{event.cropped_images.length - 5}</div>
                    <div className="text-xs">more</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

const MQTTEventFeed: React.FC<MQTTEventFeedProps> = ({ events, className }) => {
  const sortedEvents = [...events].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div className={cn('space-y-0', className)}>
      {sortedEvents.length === 0 ? (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-gray-100 rounded-full mx-auto mb-4 flex items-center justify-center">
            <span className="text-2xl text-gray-400">📡</span>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Events</h3>
          <p className="text-gray-500 text-sm">
            No detection events have been received yet.
          </p>
        </div>
      ) : (
        <>
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Activity Feed</h2>
            <p className="text-sm text-gray-600 mt-1">
              {sortedEvents.length} recent detection{sortedEvents.length !== 1 ? 's' : ''}
            </p>
          </div>
          {sortedEvents.map((event) => (
            <EventItem key={event.id} event={event} />
          ))}
        </>
      )}
    </div>
  );
};

export default MQTTEventFeed;