'use client';

import 'leaflet/dist/leaflet.css';

import React, { useCallback, useMemo, useRef, useState } from 'react';
import useOrganization from '@/hooks/use-organization';
import { usePubSub } from '@/hooks/use-pub-sub';
import { MapPin, Shield, Zap } from 'lucide-react';
import dynamic from 'next/dynamic';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

import { CroppedImage, Machine } from '@/lib/types/machine';
import {
  cn,
  countMachinesByStatus,
} from '@/lib/utils';
import { calculateSeverity } from '@/lib/utils/severity';
import { FeedEvent } from '@/lib/types/activity';

// import EventNotification from './event-notification';

interface EventMessage {
  eventstr?: string;
  original_image_path?: string;
  cropped_images?: CroppedImage[];
}

const ReactLeafletMap = dynamic(() => import('./react-leaflet-map'), {
  ssr: false,
});

const globalProcessedEvents = new Set<string>();

export default function LiveFeedWrapper({ machines }: { machines: Machine[] }) {
  const { organizationId } = useOrganization();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [machineEvents, setMachineEvents] = useState<
    Record<number, FeedEvent[]>
  >({});
  const [pulsatingMachines, setPulsatingMachines] = useState<
    Record<number, boolean>
  >({});
  // const [currentNotification, setCurrentNotification] = useState<{
  //   event: MachineEvent;
  //   machineName: string;
  // } | null>(null);

  const processedEventKeysRef = useRef(new Set<string>());

  const mqttTopics = useMemo(() => {
    if (!machines.length) return [];
    const topics = machines.map(
      (machine) => `${organizationId}/_all_/+/${machine.id}/_all_/events/#`,
    );
    console.log('📡 [MapView] Subscribing to MQTT topics:', topics);
    return topics;
  }, [organizationId, machines]);

  const extractMachineIdFromTopic = useCallback(
    (topic: string): number | null => {
      const machineId = parseInt(topic.split('/')[3]);
      return !isNaN(machineId) ? machineId : null;
    },
    [],
  );

  const startPulsatingAnimation = useCallback((machineId: number) => {
    console.log(
      '🎯 [MapView] Starting pulsating animation for machine:',
      machineId,
    );
    setPulsatingMachines((prev) => {
      console.log(
        '🔄 [MapView] Setting pulsating state for machine:',
        machineId,
        'to true',
      );
      return { ...prev, [machineId]: true };
    });
    setTimeout(() => {
      console.log(
        '⏹️ [MapView] Stopping pulsating animation for machine:',
        machineId,
      );
      setPulsatingMachines((prev) => ({ ...prev, [machineId]: false }));
    }, 3000); // Reduced to 3 seconds for better visibility
  }, []);

  const handleMqttMessage = useCallback(
    (topic: string, data: EventMessage) => {
      console.log('🔔 [MapView] MQTT message received:', { topic, data });

      const machineId = extractMachineIdFromTopic(topic);
      if (!machineId) {
        console.log(
          '❌ [MapView] Could not extract machine ID from topic:',
          topic,
        );
        return;
      }

      console.log('✅ [MapView] Extracted machine ID:', machineId);

      const eventKey = `livefeed_${data.original_image_path}_${machineId}`;
      if (
        processedEventKeysRef.current.has(eventKey) ||
        globalProcessedEvents.has(eventKey)
      ) {
        console.log('🔄 [MapView] Duplicate event, skipping:', eventKey);
        return;
      }

      processedEventKeysRef.current.add(eventKey);
      globalProcessedEvents.add(eventKey);

      const severity = calculateSeverity(data.cropped_images || []);
      const classNames =
        data.cropped_images?.map((c) => c.class_name).join(', ') || 'Event';

      console.log('📊 [MapView] Event details:', {
        severity,
        classNames,
        machineId,
      });

      // const newEvent: FeedEvent = {
      //   id: generateEventId(),
      //   timestamp: new Date(),
      //   eventstr: data.eventstr || classNames,
      //   original_image_path: data.original_image_path,
      //   cropped_images: data.cropped_images || [],
      //   severity: severity,
      // };

      // setMachineEvents((prev) => ({
      //   ...prev,
      //   [machineId]: [newEvent, ...(prev[machineId] || [])].slice(
      //     0,
      //     MAX_EVENTS_PER_MACHINE,
      //   ),
      // }));

      console.log(
        '🚀 [MapView] Starting pulsating animation for machine:',
        machineId,
      );
      startPulsatingAnimation(machineId);

      // Show notification for new events
      // const machine = machines.find(m => m.id === machineId);
      // if (machine && severity > 0) {
      // setCurrentNotification({
      //   event: newEvent,
      //   machineName: machine.name || `Machine ${machineId}`
      // });
      // }
    },
    [extractMachineIdFromTopic, startPulsatingAnimation, machines],
  );

  usePubSub(mqttTopics, handleMqttMessage, {
    autoReconnect: true,
    parseJson: true,
  });

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    setMachineEvents({});
    setPulsatingMachines({});
    processedEventKeysRef.current.clear();
    globalProcessedEvents.clear();
    setTimeout(() => setIsRefreshing(false), 1500);
  }, []);

  const { online: onlineCount, offline: offlineCount } =
    countMachinesByStatus(machines);
  const totalEvents = Object.values(machineEvents).reduce(
    (sum, events) => sum + events.length,
    0,
  );
  const criticalEvents = Object.values(machineEvents)
    .flat()
    .filter((event) => event.severity >= 2).length;

  return (
    <div className="flex h-full w-full flex-col">
      {/* Simplified header */}
      <div className="flex items-center justify-between border-b bg-white p-4 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <MapPin className="h-5 w-5 text-blue-600" />
            <span className="text-lg font-semibold text-gray-900">
              Live Map View
            </span>
          </div>

          {/* Status indicators */}
          <div className="flex items-center gap-3">
            <Badge
              variant="outline"
              className="border-green-200 bg-green-50 text-green-700"
            >
              <div className="mr-2 h-2 w-2 rounded-full bg-green-500"></div>
              {onlineCount} Online
            </Badge>
            <Badge
              variant="outline"
              className="border-gray-200 bg-gray-50 text-gray-700"
            >
              <div className="mr-2 h-2 w-2 rounded-full bg-gray-500"></div>
              {offlineCount} Offline
            </Badge>
            {totalEvents > 0 && (
              <Badge
                variant="outline"
                className="border-blue-200 bg-blue-50 text-blue-700"
              >
                <Zap className="mr-1 h-3 w-3" />
                {totalEvents} Events
              </Badge>
            )}
            {criticalEvents > 0 && (
              <Badge variant="destructive" className="animate-pulse">
                <Shield className="mr-1 h-3 w-3" />
                {criticalEvents} Critical
              </Badge>
            )}
          </div>
        </div>

        {/* Test and refresh buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              // Test ripple effect on first machine
              if (machines.length > 0) {
                console.log(
                  '🧪 [MapView] Testing ripple effect on machine:',
                  machines[0].id,
                );
                startPulsatingAnimation(machines[0].id);
              }
            }}
            className="hover:bg-blue-50"
          >
            🧪 Test Ripple
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="hover:bg-blue-50"
          >
            <div
              className={cn(
                'mr-2 h-4 w-4 transition-transform',
                isRefreshing && 'animate-spin',
              )}
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            </div>
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>
      </div>

      {/* Map container */}
      <div className="relative flex-1 overflow-hidden">
        <ReactLeafletMap
          machines={machines}
          machineEvents={machineEvents}
          pulsatingMachines={pulsatingMachines}
        />
      </div>

      {/* Event Notifications */}
      {/* {currentNotification && (
        <EventNotification
          event={currentNotification.event}
          machineName={currentNotification.machineName}
          onClose={() => setCurrentNotification(null)}
        />
      )} */}
    </div>
  );
}
