'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { usePubSub } from '@/hooks/use-pub-sub';
import useToken from '@/hooks/use-token';
import {
  Bell,
  Camera,
  CheckCircle,
  Clock,
  Image as ImageIcon,
  Loader2,
  Play,
  Volume2,
  VolumeX,
  Wifi,
  X,
} from 'lucide-react';
import Image from 'next/image';
import { toast } from 'sonner';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';

import { API_BASE_URL } from '@/lib/constants';
import { fetcherClient } from '@/lib/fetcher-client';
import { Machine } from '@/lib/types/machine';
import { cn } from '@/lib/utils';

import { AudioManager } from './audio-manager';

// Types for alert system
interface EventMessage {
  eventstr?: string;
  image_c_key: string;
  image_f_key: string;
  event_severity: string;
  meta?: {
    node_id: string;
    hb_count: string;
    last_hb_time: string;
    photos_taken: string;
    events_seen: string;
  };
}

interface EventAlert {
  id: string;
  timestamp: Date;
  machineId: string;
  machineName: string;
  message: EventMessage;
  croppedImageUrl?: string;
  fullImageUrl?: string;
  acknowledged: boolean;
  imagesFetched: boolean;
  fetchingImages: boolean;
}

interface AlertSystemProps {
  organizationId: string;
  machines: Machine[];
  onAlertReceived?: (alert: EventAlert) => void;
  enableSound?: boolean;
  useAlertTopics?: boolean; // Whether to use separate alert topics
  severityThreshold?: number; // Only process events above this severity
}

const globalAlertProcessedEvents = new Set<string>();

export default function CriticalAlertSystem({
  organizationId,
  machines,
  onAlertReceived = (alert) => {
    console.log('🚨 Alert received:', alert);
  },
  enableSound = true,
  severityThreshold = 1,
}: AlertSystemProps) {
  const { token } = useToken();
  const [alerts, setAlerts] = useState<EventAlert[]>([]);
  const [isAudioEnabled, setIsAudioEnabled] = useState(enableSound);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [volume, setVolume] = useState(0.7);
  const [unacknowledgedCount, setUnacknowledgedCount] = useState(0);

  const audioManagerRef = useRef(new AudioManager());
  const flashIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const processedEventKeysRef = useRef(new Set<string>());

  // FIXED: Generate topics that match the live feed pattern exactly
  const topics = React.useMemo(() => {
    if (machines.length === 0) {
      console.log('⚠️ [AlertSystem] No machines provided');
      return [];
    }

    const generatedTopics = machines.map(
      (machine) => `${organizationId}/_all_/+/${machine.id}/_all_/EVENT/#`,
    );

    console.log('🎯 [AlertSystem] Generated topics:', generatedTopics);
    return generatedTopics;
  }, [organizationId, machines]);

  // Initialize audio with better error handling
  useEffect(() => {
    const initAudio = async () => {
      if (isAudioEnabled) {
        console.log('🔊 [AlertSystem] Initializing audio...');
        try {
          await audioManagerRef.current.initialize();
          console.log('✅ [AlertSystem] Audio initialized successfully');
        } catch (error) {
          console.error('❌ [AlertSystem] Audio initialization failed:', error);
        }
      }
    };

    const handleUserInteraction = () => {
      initAudio();
      document.removeEventListener('click', handleUserInteraction);
      document.removeEventListener('keydown', handleUserInteraction);
      document.removeEventListener('touchstart', handleUserInteraction);
    };

    // Try multiple event types for better browser compatibility
    document.addEventListener('click', handleUserInteraction);
    document.addEventListener('keydown', handleUserInteraction);
    document.addEventListener('touchstart', handleUserInteraction);

    // Also try to initialize immediately
    initAudio();

    return () => {
      document.removeEventListener('click', handleUserInteraction);
      document.removeEventListener('keydown', handleUserInteraction);
      document.removeEventListener('touchstart', handleUserInteraction);
    };
  }, [isAudioEnabled]);

  // Flash effect for critical alerts
  const startFlashing = useCallback(() => {
    if (flashIntervalRef.current) return;

    console.log('🚨 [AlertSystem] Starting screen flash');
    let isRed = false;
    flashIntervalRef.current = setInterval(() => {
      document.body.style.backgroundColor = isRed
        ? ''
        : 'rgba(239, 68, 68, 0.1)';
      isRed = !isRed;
    }, 500);

    setTimeout(() => {
      if (flashIntervalRef.current) {
        clearInterval(flashIntervalRef.current);
        flashIntervalRef.current = null;
        document.body.style.backgroundColor = '';
        console.log('⏹️ [AlertSystem] Screen flash stopped');
      }
    }, 5000);
  }, []);

  // Fetch images from Django backend
  const fetchEventImages = async (imageKeys: {
    image_c_key: string;
    image_f_key: string;
  }) => {
    try {
      if (!token) {
        console.log('⚠️ [AlertSystem] No token for image fetching');
        return null;
      }

      console.log('📸 [AlertSystem] Fetching images:', imageKeys);
      const data = await fetcherClient<{
        success: boolean;
        cropped_image_url: string;
        full_image_url: string;
        error?: string;
      }>(`${API_BASE_URL}/event-images/`, token, {
        method: 'POST',
        body: imageKeys,
      });

      if (data?.success) {
        console.log('✅ [AlertSystem] Images fetched successfully');
        return {
          croppedImageUrl: data.cropped_image_url,
          fullImageUrl: data.full_image_url,
        };
      } else {
        throw new Error(data?.error || 'Failed to fetch images');
      }
    } catch (error) {
      console.error('❌ [AlertSystem] Error fetching images:', error);
      return null;
    }
  };

  const handleMqttMessage = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async (topic: string, data: any) => {
      const now = new Date();

      console.log('📥 [AlertSystem] MQTT message received:', {
        topic,
        data: JSON.stringify(data).substring(0, 200),
        timestamp: now.toISOString(),
      });

      try {
        // Extract machine ID from topic
        const topicParts = topic.split('/');
        const machineId = topicParts[3];

        console.log('🔍 [AlertSystem] Parsed topic:', {
          topicParts,
          machineId,
        });

        // Find machine info
        const machine = machines.find((m) => m.id === parseInt(machineId));
        const machineName = machine?.name || `Machine-${machineId}`;

        console.log('🏭 [AlertSystem] Machine info:', {
          machineId,
          machineName,
          found: !!machine,
        });

        // Parse event message
        const eventMessage: EventMessage = data;
        const severity = parseInt(eventMessage.event_severity || '0');

        console.log('📊 [AlertSystem] Event details:', {
          severity,
          severityThreshold,
          eventstr: eventMessage.eventstr,
          hasImageKeys: !!(
            eventMessage.image_c_key && eventMessage.image_f_key
          ),
          imageKeys: {
            c_key: eventMessage.image_c_key,
            f_key: eventMessage.image_f_key,
          },
        });

        // Check severity threshold
        if (severity < severityThreshold) {
          console.log(
            `⚠️ [AlertSystem] Severity ${severity} < threshold ${severityThreshold}, filtering out`,
          );
          return;
        }

        // Create event key for deduplication
        const eventKey = `alert_${eventMessage.image_f_key}_${eventMessage.image_c_key}_${machineId}_${severity}`;
        console.log('🔑 [AlertSystem] Event key:', eventKey);

        // Check for duplicates
        if (
          processedEventKeysRef.current.has(eventKey) ||
          globalAlertProcessedEvents.has(eventKey)
        ) {
          console.log(`🔄 [AlertSystem] Duplicate detected: ${eventKey}`);
          return;
        }

        // Mark as processed
        processedEventKeysRef.current.add(eventKey);
        globalAlertProcessedEvents.add(eventKey);

        // Cleanup old entries
        if (globalAlertProcessedEvents.size > 500) {
          const entries = Array.from(globalAlertProcessedEvents);
          const toRemove = entries.slice(0, entries.length - 400);
          toRemove.forEach((key) => globalAlertProcessedEvents.delete(key));
          console.log('🧹 [AlertSystem] Cleaned up old processed events');
        }

        console.log('✅ [AlertSystem] Creating new alert for event:', eventKey);

        // Create alert
        const alert: EventAlert = {
          id: `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
          machineId,
          machineName,
          message: eventMessage,
          acknowledged: false,
          imagesFetched: false,
          fetchingImages: false,
        };

        // Add to state
        setAlerts((prev) => [alert, ...prev.slice(0, 49)]);
        setUnacknowledgedCount((prev) => prev + 1);

        // Play audio
        if (isAudioEnabled && severity >= severityThreshold) {
          console.log('🔊 [AlertSystem] Playing alarm for severity', severity);
          try {
            await audioManagerRef.current.playAlarm(volume);
            console.log('✅ [AlertSystem] Alarm played successfully');
          } catch (error) {
            console.error('❌ [AlertSystem] Failed to play alarm:', error);
          }
        } else {
          console.log(
            '🔇 [AlertSystem] Audio disabled or severity too low, skipping sound',
          );
        }

        // Flash for critical alerts
        if (severity >= 3) {
          startFlashing();
        }

        // Show toast
        toast.custom(
          (t) => (
            <div className="flex w-full max-w-md items-center justify-between rounded-lg border border-red-400 bg-red-50 p-3 shadow-lg">
              <div className="flex items-center gap-3">
                <Camera className="h-5 w-5 text-red-500" />
                <div>
                  <p className="text-sm font-semibold text-gray-900">
                    🚨 ALERT
                  </p>
                  <p className="text-sm text-gray-700">
                    {machineName}: Severity {severity}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => toast.dismiss(t)}
                className="ml-2"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ),
          {
            duration: 5000,
            id: alert.id,
            position: 'bottom-right',
          },
        );

        // Callback
        if (onAlertReceived) {
          onAlertReceived(alert);
        }

        console.log('🎉 [AlertSystem] Alert processing complete');
      } catch (error) {
        console.error('❌ [AlertSystem] Error processing MQTT message:', error);
      }
    },
    [
      machines,
      isAudioEnabled,
      volume,
      startFlashing,
      onAlertReceived,
      severityThreshold,
    ],
  );

  // Use PubSub hook
  const { isConnected, error } = usePubSub(topics, handleMqttMessage, {
    autoReconnect: true,
    parseJson: true,
    enableBufferedMessages: false,
  });

  useEffect(() => {
    if (isConnected) {
      console.log('✅ [AlertSystem] MQTT connected to topics:', topics);
    } else if (error) {
      console.error('❌ [AlertSystem] MQTT error:', error);
    } else {
      console.log('🔄 [AlertSystem] MQTT connecting...');
    }
  }, [isConnected, error, topics]);

  // Test functions
  const testAudio = async () => {
    console.log('🧪 [AlertSystem] Testing audio manually...');
    try {
      await audioManagerRef.current.playAlarm(volume);
      console.log('✅ [AlertSystem] Test audio played successfully');
      toast.success('Audio test successful!');
    } catch (error) {
      console.error('❌ [AlertSystem] Test audio failed:', error);
      toast.error('Audio test failed: ' + error);
    }
  };

  // Polling for images
  useEffect(() => {
    const pollForImages = async () => {
      const alertsNeedingImages = alerts.filter(
        (alert) => !alert.imagesFetched && !alert.fetchingImages,
      );

      if (alertsNeedingImages.length === 0) return;

      setAlerts((prev) =>
        prev.map((alert) =>
          alertsNeedingImages.some((a) => a.id === alert.id)
            ? { ...alert, fetchingImages: true }
            : alert,
        ),
      );

      for (const alert of alertsNeedingImages) {
        try {
          const imageUrls = await fetchEventImages({
            image_c_key: alert.message.image_c_key,
            image_f_key: alert.message.image_f_key,
          });

          setAlerts((prev) =>
            prev.map((a) =>
              a.id === alert.id
                ? {
                    ...a,
                    croppedImageUrl: imageUrls?.croppedImageUrl,
                    fullImageUrl: imageUrls?.fullImageUrl,
                    imagesFetched: true,
                    fetchingImages: false,
                  }
                : a,
            ),
          );
        } catch (error) {
          console.error(`Failed to fetch images for alert ${alert.id}:`, error);
          setAlerts((prev) =>
            prev.map((a) =>
              a.id === alert.id ? { ...a, fetchingImages: false } : a,
            ),
          );
        }
      }
    };

    const interval = setInterval(pollForImages, 5000);
    return () => clearInterval(interval);
  }, [alerts, token]);

  // Alert management functions
  const acknowledgeAlert = useCallback((alertId: string) => {
    setAlerts((prev) =>
      prev.map((alert) =>
        alert.id === alertId ? { ...alert, acknowledged: true } : alert,
      ),
    );
    setUnacknowledgedCount((prev) => Math.max(0, prev - 1));
  }, []);

  const acknowledgeAll = useCallback(() => {
    setAlerts((prev) =>
      prev.map((alert) => ({ ...alert, acknowledged: true })),
    );
    setUnacknowledgedCount(0);
  }, []);

  const clearAll = useCallback(() => {
    setAlerts([]);
    setUnacknowledgedCount(0);
    processedEventKeysRef.current.clear();
    globalAlertProcessedEvents.clear();
  }, []);

  // Click outside handler
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        modalRef.current &&
        !modalRef.current.contains(event.target as Node)
      ) {
        setIsModalOpen(false);
      }
    };

    if (isModalOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    } else {
      document.removeEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isModalOpen]);

  const getTimeElapsed = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    return minutes > 0 ? `${minutes}m ${seconds}s ago` : `${seconds}s ago`;
  };

  return (
    <>
      {/* Alert Button with Debug Panel */}
      <div className="fixed top-4 right-4 z-50">
        <div className="flex flex-col items-end gap-2">
          {/* Main Alert Button */}
          <Button
            onClick={() => setIsModalOpen(!isModalOpen)}
            className={cn(
              'relative',
              unacknowledgedCount > 0
                ? 'animate-pulse bg-red-500 hover:bg-red-600'
                : '',
            )}
            size="lg"
          >
            <Bell className="mr-2 h-5 w-5" />
            Alerts
            {unacknowledgedCount > 0 && (
              <Badge className="absolute -top-2 -right-2 h-5 min-w-[20px] bg-yellow-500 px-1 text-black">
                {unacknowledgedCount > 99 ? '99+' : unacknowledgedCount}
              </Badge>
            )}
          </Button>
        </div>
      </div>

      {/* Alert Modal */}
      {isModalOpen && (
        <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-black/50 p-4">
          <Card
            className="h-full w-full max-w-4xl overflow-hidden"
            ref={modalRef}
          >
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Camera className="h-5 w-5 text-red-500" />
                  Critical Alert System
                  {unacknowledgedCount > 0 && (
                    <Badge variant="destructive">
                      {unacknowledgedCount} New
                    </Badge>
                  )}
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsAudioEnabled(!isAudioEnabled)}
                    title="Toggle Audio"
                  >
                    {isAudioEnabled ? (
                      <Volume2 className="h-4 w-4" />
                    ) : (
                      <VolumeX className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={testAudio}
                    title="Test Audio"
                  >
                    <Play className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsModalOpen(false)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Controls */}
              <div className="mt-2 flex gap-2">
                {unacknowledgedCount > 0 && (
                  <Button size="sm" onClick={acknowledgeAll} className="flex-1">
                    <CheckCircle className="mr-1 h-4 w-4" />
                    Acknowledge All
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={clearAll}
                  className="flex-1"
                >
                  Clear All
                </Button>
              </div>

              {/* Volume Control */}
              {isAudioEnabled && (
                <div className="mt-2 flex items-center gap-2">
                  <VolumeX className="h-4 w-4" />
                  <Input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={volume}
                    onChange={(e) => setVolume(parseFloat(e.target.value))}
                    className="flex-1"
                  />
                  <Volume2 className="h-4 w-4" />
                  <span className="w-8 text-xs">
                    {Math.round(volume * 100)}%
                  </span>
                </div>
              )}
            </CardHeader>

            <CardContent className="p-0">
              {/* Status */}
              <div className="px-4 pb-3">
                <Alert
                  className={cn(
                    isConnected
                      ? 'border-green-200 bg-green-50'
                      : 'border-red-200 bg-red-50',
                  )}
                >
                  <Wifi
                    className={cn(
                      'h-4 w-4',
                      isConnected ? 'text-green-600' : 'text-red-600',
                    )}
                  />
                  <AlertDescription
                    className={cn(
                      isConnected ? 'text-green-800' : 'text-red-800',
                    )}
                  >
                    {isConnected
                      ? `Connected - Monitoring ${machines.length} machines (Severity ≥ ${severityThreshold})`
                      : error
                        ? `Connection Error: ${error.message}`
                        : 'Connecting...'}
                  </AlertDescription>
                </Alert>
              </div>

              <Separator />

              {/* Alerts List */}
              <div className="max-h-[60vh] overflow-y-auto">
                {alerts.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <Camera className="mx-auto mb-2 h-12 w-12 opacity-30" />
                    <p>No alerts detected</p>
                    <p className="text-sm">
                      Monitoring severity ≥ {severityThreshold}...
                    </p>
                  </div>
                ) : (
                  <div className="grid gap-4 p-4">
                    {alerts.map((alert) => (
                      <div
                        key={alert.id}
                        className={cn(
                          'rounded-lg border p-4 transition-all',
                          alert.acknowledged
                            ? 'border-gray-200 bg-gray-50'
                            : parseInt(alert.message.event_severity) >= 3
                              ? 'border-red-200 bg-red-50 shadow-md'
                              : 'border-orange-200 bg-orange-50',
                        )}
                      >
                        <div className="mb-3 flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            <Camera className="h-5 w-5 text-red-500" />
                            <div>
                              <Badge variant="destructive" className="text-xs">
                                🚨 ALERT
                              </Badge>
                              {!alert.acknowledged && (
                                <Badge
                                  variant="outline"
                                  className="ml-1 text-xs"
                                >
                                  NEW
                                </Badge>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3 text-gray-400" />
                            <span className="text-xs text-gray-500">
                              {getTimeElapsed(alert.timestamp)}
                            </span>
                          </div>
                        </div>

                        <div className="mb-3">
                          <div className="mb-1 font-medium text-gray-900">
                            {alert.machineName}
                          </div>
                          <div className="text-sm text-gray-600">
                            Event: {alert.message.eventstr || 'No description'}
                          </div>
                          <div className="text-sm text-gray-600">
                            Severity: {alert.message.event_severity}(
                            {alert.message.event_severity === '1'
                              ? 'Low'
                              : alert.message.event_severity === '2'
                                ? 'High'
                                : 'Critical'}
                            )
                          </div>
                        </div>

                        {/* Image Display */}
                        <div className="mb-3">
                          {alert.fetchingImages ? (
                            <div className="flex items-center gap-2 text-sm text-gray-500">
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Fetching images...
                            </div>
                          ) : alert.imagesFetched ? (
                            <div className="flex items-center gap-2">
                              {alert.croppedImageUrl && (
                                <div>
                                  <p className="mb-1 text-xs text-gray-500">
                                    Cropped
                                  </p>
                                  <Image
                                    width={100}
                                    height={100}
                                    src={alert.croppedImageUrl}
                                    alt="Cropped event image"
                                    className="h-80 w-fit rounded border object-contain"
                                  />
                                </div>
                              )}
                              {alert.fullImageUrl && (
                                <div>
                                  <p className="mb-1 text-xs text-gray-500">
                                    Full
                                  </p>
                                  <Image
                                    width={100}
                                    height={100}
                                    src={alert.fullImageUrl}
                                    alt="Full event image"
                                    className="h-80 w-fit rounded border object-contain"
                                  />
                                </div>
                              )}
                            </div>
                          ) : (
                            <div className="flex items-center gap-2 text-sm text-gray-500">
                              <ImageIcon className="h-4 w-4" />
                              Images not available yet...
                            </div>
                          )}
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="text-xs text-gray-500">
                            Machine ID: {alert.machineId}
                          </div>
                          {!alert.acknowledged && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => acknowledgeAlert(alert.id)}
                              className="text-xs"
                            >
                              <CheckCircle className="mr-1 h-3 w-3" />
                              Acknowledge
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
