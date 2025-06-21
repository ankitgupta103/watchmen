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
  image_c_key: string;
  image_f_key: string;
  event_severity: string;
  meta: {
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
    console.log('alert received', alert);
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

  // Generate topics - use separate alert topics if specified
  const topics = React.useMemo(() => {
    if (machines.length === 0) return [];

    // Use same topics as live feed (default behavior)
    // const today = new Date().toISOString().split('T')[0]; // yyyy-mm-dd format
    return machines.map(
      (machine) =>
        `${organizationId}/_all_/+/${machine.id}/_all_/EVENT/#`,
    );
  }, [organizationId, machines]);

  // Initialize audio on first user interaction
  useEffect(() => {
    const initAudio = async () => {
      await audioManagerRef.current.initialize();
    };

    const handleUserInteraction = () => {
      initAudio();
      document.removeEventListener('click', handleUserInteraction);
      document.removeEventListener('keydown', handleUserInteraction);
    };

    document.addEventListener('click', handleUserInteraction);
    document.addEventListener('keydown', handleUserInteraction);

    return () => {
      document.removeEventListener('click', handleUserInteraction);
      document.removeEventListener('keydown', handleUserInteraction);
    };
  }, []);

  // Flash effect for critical alerts
  const startFlashing = useCallback(() => {
    if (flashIntervalRef.current) return;

    let isRed = false;
    flashIntervalRef.current = setInterval(() => {
      document.body.style.backgroundColor = isRed
        ? ''
        : 'rgba(239, 68, 68, 0.1)';
      isRed = !isRed;
    }, 500);

    // Stop flashing after 10 seconds
    setTimeout(() => {
      if (flashIntervalRef.current) {
        clearInterval(flashIntervalRef.current);
        flashIntervalRef.current = null;
        document.body.style.backgroundColor = '';
      }
    }, 10000);
  }, []);

  // Fetch images from Django backend
  const fetchEventImages = async (imageKeys: {
    image_c_key: string;
    image_f_key: string;
  }) => {
    try {
      if (!token) return null;

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
        return {
          croppedImageUrl: data.cropped_image_url,
          fullImageUrl: data.full_image_url,
        };
      } else {
        throw new Error(data?.error || 'Failed to fetch images');
      }
    } catch (error) {
      console.error('Error fetching images:', error);
      return null;
    }
  };

  // Polling mechanism to fetch images every 5 seconds
  useEffect(() => {
    const pollForImages = async () => {
      const alertsNeedingImages = alerts.filter(
        (alert) => !alert.imagesFetched && !alert.fetchingImages,
      );

      if (alertsNeedingImages.length === 0) return;

      // Mark alerts as fetching to prevent duplicate requests
      setAlerts((prev) =>
        prev.map((alert) =>
          alertsNeedingImages.some((a) => a.id === alert.id)
            ? { ...alert, fetchingImages: true }
            : alert,
        ),
      );

      // Try to fetch images for each alert
      for (const alert of alertsNeedingImages) {
        try {
          const imageUrls = await fetchEventImages({
            image_c_key: alert.message.image_c_key,
            image_f_key: alert.message.image_f_key,
          });

          // Update alert with image URLs
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
          // Reset fetching state on error
          setAlerts((prev) =>
            prev.map((a) =>
              a.id === alert.id ? { ...a, fetchingImages: false } : a,
            ),
          );
        }
      }
    };

    // Start polling every 5 seconds
    const interval = setInterval(pollForImages, 5000);

    return () => {
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alerts, token]);

  // Handle MQTT message with improved duplicate detection
  const handleMqttMessage = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async (topic: string, data: any) => {
      try {
        // Extract machine ID from topic
        const topicParts = topic.split('/');
        const machineId = topicParts[3]; // Based on pattern: {orgId}/_all_/yyyy-mm-dd/{machineId}/EVENT/# or {orgId}/_all_/ALERT/{machineId}/EVENT/#

        // Find machine name
        const machine = machines.find((m) => m.id === parseInt(machineId));
        const machineName = machine?.name || `Machine-${machineId}`;

        // Parse the event message
        const eventMessage: EventMessage = data;
        const severity = parseInt(eventMessage.event_severity);

        // Filter by severity threshold
        if (severity < severityThreshold) {
          console.log(
            `[CriticalAlertSystem] Event severity ${severity} below threshold ${severityThreshold}, ignoring`,
          );
          return;
        }

        // Create enhanced event key for deduplication
        const eventKey = `alert_${eventMessage.image_f_key}_${eventMessage.image_c_key}_${machineId}_${severity}`;

        // Check for duplicates using both local and global tracking
        if (
          processedEventKeysRef.current.has(eventKey) ||
          globalAlertProcessedEvents.has(eventKey)
        ) {
          console.log(
            `[CriticalAlertSystem] Duplicate alert detected: ${eventKey}`,
          );
          return;
        }

        // Add to both local and global processed events
        processedEventKeysRef.current.add(eventKey);
        globalAlertProcessedEvents.add(eventKey);

        // Clean up old entries to prevent memory leaks
        if (globalAlertProcessedEvents.size > 500) {
          const entries = Array.from(globalAlertProcessedEvents);
          const toRemove = entries.slice(0, entries.length - 400);
          toRemove.forEach((key) => globalAlertProcessedEvents.delete(key));
        }

        console.log(
          `[CriticalAlertSystem] Processing new alert: ${eventKey} for machine ${machineId}`,
        );

        // Create alert (without images initially)
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

        // Add alert to state
        setAlerts((prev) => [alert, ...prev.slice(0, 49)]); // Keep last 50 alerts
        setUnacknowledgedCount((prev) => prev + 1);

        // Play alarm sound only for severity threshold or higher
        if (isAudioEnabled && severity >= severityThreshold) {
          try {
            await audioManagerRef.current.playAlarm(volume);
          } catch (error) {
            console.warn('Failed to play alarm sound:', error);
          }
        }

        // Flash screen only for critical alerts
        if (severity >= 3) {
          startFlashing();
        }

        // Show toast notification
        toast.custom(
          (t) => (
            <div className="flex w-full max-w-md items-center justify-between rounded-lg border border-red-400 bg-red-50 p-3 shadow-lg">
              <div className="flex items-center gap-3">
                <Camera className="h-5 w-5 text-red-500" />
                <div>
                  <p className="text-sm font-semibold text-gray-900">
                    CRITICAL ALERT
                  </p>
                  <p className="text-sm text-gray-700">
                    {machineName}:{' '}
                    {severity === 1
                      ? 'Low'
                      : severity === 2
                        ? 'High'
                        : 'Critical'}
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
            duration: 7000,
            id: alert.id,
            position: 'bottom-right',
          },
        );

        // Callback for parent component
        if (onAlertReceived) {
          onAlertReceived(alert);
        }
      } catch (error) {
        console.error('Error handling MQTT message in alert system:', error);
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

  // Use the PubSub hook with buffered messages disabled to prevent duplicates
  const { isConnected, error } = usePubSub(topics, handleMqttMessage, {
    autoReconnect: true,
    parseJson: true,
    enableBufferedMessages: false, // Disable buffered messages for alerts
  });

  // Acknowledge alert
  const acknowledgeAlert = useCallback((alertId: string) => {
    setAlerts((prev) =>
      prev.map((alert) =>
        alert.id === alertId ? { ...alert, acknowledged: true } : alert,
      ),
    );
    setUnacknowledgedCount((prev) => Math.max(0, prev - 1));
  }, []);

  // Acknowledge all alerts
  const acknowledgeAll = useCallback(() => {
    setAlerts((prev) =>
      prev.map((alert) => ({ ...alert, acknowledged: true })),
    );
    setUnacknowledgedCount(0);
  }, []);

  // Clear all alerts
  const clearAll = useCallback(() => {
    setAlerts([]);
    setUnacknowledgedCount(0);
    // Clear processed keys
    processedEventKeysRef.current.clear();
    globalAlertProcessedEvents.clear();
  }, []);

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

  // Format time elapsed
  const getTimeElapsed = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);

    if (minutes > 0) {
      return `${minutes}m ${seconds}s ago`;
    }
    return `${seconds}s ago`;
  };

  return (
    <>
      {/* Alert Trigger Button */}
      <div className="fixed top-4 right-4 z-50">
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

      {/* Alert Panel (Modal) */}
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
                  Critical Alerts
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
                    Ack All
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
                    <p>No critical alerts</p>
                    <p className="text-sm">
                      System is monitoring for severity ≥ {severityThreshold}...
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
                                CRITICAL ALERT
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
                            Severity:{' '}
                            {alert.message.event_severity === '1'
                              ? 'Low'
                              : alert.message.event_severity === '2'
                                ? 'High'
                                : 'Critical'}
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
