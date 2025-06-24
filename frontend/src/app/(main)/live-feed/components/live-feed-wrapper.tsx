'use client';

import 'leaflet/dist/leaflet.css';

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import useAllMachineStats from '@/hooks/use-all-machine-stats';
import useOrganization from '@/hooks/use-organization';
import { usePubSub } from '@/hooks/use-pub-sub';
import useToken from '@/hooks/use-token';
import { Calendar, RefreshCw, Shield } from 'lucide-react';
import dynamic from 'next/dynamic';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import { Machine, MachineData } from '@/lib/types/machine';
import {
  cn,
  countMachinesByStatus,
  generateEventId,
  hasCriticalEvents,
  isMachineOnline,
  MAX_EVENT_COUNT_FOR_COLOR,
  MAX_EVENTS_PER_MACHINE,
  PULSATING_DURATION_MS,
} from '@/lib/utils';

import MachineDetailModal from './machine-detail-modal';

interface LiveFeedWrapperProps {
  machines: Machine[];
  selectedDate?: Date;
}

interface MachineEvent {
  id: string;
  timestamp: Date;
  eventstr: string;
  image_c_key?: string;
  image_f_key?: string;
  event_severity?: string;
}

interface EventMessage {
  eventstr?: string;
  image_c_key: string;
  image_f_key: string;
  event_severity: string;
}

const ReactLeafletMap = dynamic(() => import('./react-leaflet-map'), {
  ssr: false,
});

// Global processed events tracker for live feed
const globalProcessedEvents = new Set<string>();

export default function LiveFeedWrapper({
  machines,
  selectedDate,
}: LiveFeedWrapperProps) {
  const { organizationId } = useOrganization();
  const { token } = useToken();
  const [selectedMachine, setSelectedMachine] = useState<Machine | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const [machineEvents, setMachineEvents] = useState<
    Record<number, MachineEvent[]>
  >({});

  // Use ref for processed events to avoid stale closures
  const processedEventKeysRef = useRef(new Set<string>());

  const [machineEventCounts, setMachineEventCounts] = useState<
    Record<number, number>
  >({});

  const [pulsatingMachines, setPulsatingMachines] = useState<
    Record<number, boolean>
  >({});

  const machineStats = useAllMachineStats(machines);

  // FIXED: Stable topics array using useMemo - same pattern as alert system
  const mqttTopics = useMemo(() => {
    if (machines.length === 0) {
      console.log('⚠️ [LiveFeed] No machines provided');
      return [];
    }

    const topics = machines.map(
      (machine) => `${organizationId}/_all_/+/${machine.id}/_all_/EVENT/#`,
    );

    console.log('🎯 [LiveFeed] Generated topics:', topics);
    return topics;
  }, [organizationId, machines]);

  const extractMachineIdFromTopic = useCallback(
    (topic: string): number | null => {
      const topicParts = topic.split('/');
      const machineIdPart = topicParts[3];

      if (machineIdPart && machineIdPart !== '_all_') {
        const machineId = parseInt(machineIdPart);
        return !isNaN(machineId) ? machineId : null;
      }
      return null;
    },
    [],
  );

  const createMachineEvent = useCallback(
    (eventMessage: EventMessage): MachineEvent => {
      return {
        id: generateEventId(),
        timestamp: new Date(),
        eventstr:
          eventMessage.eventstr ||
          `Event - Severity ${eventMessage.event_severity}`,
        image_c_key: eventMessage.image_c_key,
        image_f_key: eventMessage.image_f_key,
        event_severity: eventMessage.event_severity.toString(),
      };
    },
    [],
  );

  const addEventToMachine = useCallback(
    (machineId: number, newEvent: MachineEvent) => {
      setMachineEvents((prev) => {
        const currentEvents = prev[machineId] || [];
        const updatedEvents = [newEvent, ...currentEvents].slice(
          0,
          MAX_EVENTS_PER_MACHINE,
        );
        return { ...prev, [machineId]: updatedEvents };
      });
    },
    [],
  );

  const incrementEventCount = useCallback((machineId: number) => {
    setMachineEventCounts((prev) => ({
      ...prev,
      [machineId]: Math.min(
        (prev[machineId] || 0) + 1,
        MAX_EVENT_COUNT_FOR_COLOR,
      ),
    }));
  }, []);

  const startPulsatingAnimation = useCallback((machineId: number) => {
    setPulsatingMachines((prev) => ({
      ...prev,
      [machineId]: true,
    }));
    setTimeout(() => {
      setPulsatingMachines((prev) => ({ ...prev, [machineId]: false }));
    }, PULSATING_DURATION_MS);
  }, []);

  // FIXED: Enhanced message handler with better logging and NO AUDIO
  const handleMqttMessage = useCallback(
    async (topic: string, data: EventMessage) => {
      console.log('📥 [LiveFeed] MQTT message received:', {
        topic,
        data: JSON.stringify(data).substring(0, 100),
        timestamp: new Date().toISOString(),
      });

      try {
        const machineId = extractMachineIdFromTopic(topic);
        if (!machineId) {
          console.log(
            '⚠️ [LiveFeed] Could not extract machine ID from topic:',
            topic,
          );
          return;
        }

        // Create event key for deduplication - different prefix than alerts
        const eventKey = `livefeed_${data.image_f_key}_${data.image_c_key}_${machineId}_${data.event_severity}`;

        console.log('🔍 [LiveFeed] Processing event:', {
          machineId,
          eventKey,
          severity: data.event_severity,
        });

        // Check both local and global processed events
        if (
          !eventKey ||
          processedEventKeysRef.current.has(eventKey) ||
          globalProcessedEvents.has(eventKey)
        ) {
          console.log(`🔄 [LiveFeed] Duplicate event detected: ${eventKey}`);
          return;
        }

        // Add to both local and global processed events
        processedEventKeysRef.current.add(eventKey);
        globalProcessedEvents.add(eventKey);

        // Clean up old entries to prevent memory leaks
        if (globalProcessedEvents.size > 1000) {
          const entries = Array.from(globalProcessedEvents);
          const toRemove = entries.slice(0, entries.length - 800);
          toRemove.forEach((key) => globalProcessedEvents.delete(key));
          console.log('🧹 [LiveFeed] Cleaned up old processed events');
        }

        console.log(
          `✅ [LiveFeed] Processing new event: ${eventKey} for machine ${machineId}`,
        );

        const newEvent = createMachineEvent(data);
        addEventToMachine(machineId, newEvent);
        incrementEventCount(machineId);
        startPulsatingAnimation(machineId);

        // REMOVED: Audio playing - let alert system handle audio
        console.log(
          '🔇 [LiveFeed] Event processed, audio handled by alert system',
        );
      } catch (error) {
        console.error('❌ [LiveFeed] Error processing MQTT message:', error, {
          topic,
          data,
        });
      }
    },
    [
      extractMachineIdFromTopic,
      createMachineEvent,
      addEventToMachine,
      incrementEventCount,
      startPulsatingAnimation,
    ],
  );

  const { isConnected, error: mqttError } = usePubSub(
    mqttTopics,
    handleMqttMessage,
    { autoReconnect: true, parseJson: true },
  );

  useEffect(() => {
    if (isConnected) {
      console.log('✅ [LiveFeed] MQTT connected to topics:', mqttTopics);
    } else if (mqttError) {
      console.error('❌ [LiveFeed] MQTT error:', mqttError);
    } else {
      console.log('🔄 [LiveFeed] MQTT connecting...');
    }
  }, [isConnected, mqttError, mqttTopics]);

  const getMachineData = useCallback(
    (machineId: number): MachineData => {
      const events = machineEvents[machineId] || [];
      const eventCount = machineEventCounts[machineId] || 0;
      const lastEvent = events[0];
      const stats = machineStats[machineId];
      const machine = machines.find((m) => m.id === machineId);

      return {
        machine_id: machineId,
        events: events,
        event_count: eventCount,
        last_event: lastEvent,
        last_updated:
          lastEvent?.timestamp.toISOString() || new Date().toISOString(),
        is_online: machine ? isMachineOnline(machine) : false,
        location: {
          lat: stats?.data?.message?.location?.lat ?? 0,
          lng: stats?.data?.message?.location?.long ?? 0,
          timestamp: stats?.data?.message?.location?.timestamp ?? '',
        },
        stats_data: stats?.data,
        buffer_size: stats?.buffer ?? 0,
        is_pulsating: pulsatingMachines[machineId] || false,
        is_critical: hasCriticalEvents(events),
      };
    },
    [
      machineEvents,
      machineEventCounts,
      machineStats,
      pulsatingMachines,
      machines,
    ],
  );

  const totalEvents = Object.values(machineEventCounts).reduce(
    (sum, count) => sum + count,
    0,
  );
  const { online: onlineCount, offline: offlineCount } =
    countMachinesByStatus(machines);

  const filteredMachines = useMemo(() => {
    if (statusFilter === 'all') return machines;
    return machines.filter((machine) => {
      const isOnline = isMachineOnline(machine);
      if (statusFilter === 'online') return isOnline;
      if (statusFilter === 'offline') return !isOnline;

      return true;
    });
  }, [machines, statusFilter]);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    setMachineEvents({});
    setMachineEventCounts({});
    setPulsatingMachines({});

    // Clear processed keys on refresh
    processedEventKeysRef.current.clear();
    globalProcessedEvents.clear();

    setTimeout(() => setIsRefreshing(false), 1500);
  }, []);

  const handleClearAllFilters = useCallback(() => {
    setStatusFilter('all');
  }, []);

  const liveEventsForModal = selectedMachine
    ? machineEvents[selectedMachine.id] || []
    : [];

  return (
    <div className="flex h-full w-full flex-col">
      {/* Map Controls */}
      <div className="flex items-center justify-between border-b bg-white p-4 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-600" />
            <span className="font-semibold">Live Event Monitor</span>

            {/* MQTT Connection Status */}
            <div className="flex items-center gap-1 text-xs">
              <div
                className={cn(
                  'h-2 w-2 rounded-full',
                  isConnected ? 'bg-green-500' : 'bg-red-500',
                )}
              ></div>
              <span className="text-gray-500">
                {isConnected ? 'Connected' : 'Offline'}
              </span>
            </div>

            {/* Show MQTT error if any */}
            {mqttError && (
              <div className="text-xs text-red-500" title={mqttError.message}>
                Connection Error
              </div>
            )}
          </div>

          {/* Machine Stats */}
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <span>
                {onlineCount} Online
                {statusFilter === 'online'
                  ? ` (showing ${filteredMachines.length})`
                  : ''}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-gray-500"></div>
              <span>
                {offlineCount} Offline
                {statusFilter === 'offline'
                  ? ` (showing ${filteredMachines.length})`
                  : ''}
              </span>
            </div>
            {statusFilter === 'all' && (
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 rounded-full bg-blue-500"></div>
                <span>{machines.length} Total</span>
              </div>
            )}
            {totalEvents > 0 && (
              <Badge
                variant="outline"
                className="border-orange-300 text-xs text-orange-700"
              >
                {totalEvents} Event{totalEvents > 1 ? 's' : ''}
              </Badge>
            )}
            <div className="text-xs text-gray-500">
              Active: {Object.keys(machineEventCounts).length}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Date Filter */}
          {selectedDate && (
            <div className="flex items-center gap-2 rounded-md bg-blue-50 px-3 py-1 text-sm">
              <Calendar className="h-4 w-4 text-blue-600" />
              <span>{selectedDate.toLocaleDateString()}</span>
            </div>
          )}

          {/* Status Filter */}
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="All Status" />
            </SelectTrigger>
            <SelectContent className="z-[1000]">
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="online">Online Only</SelectItem>
              <SelectItem value="offline">Offline Only</SelectItem>
            </SelectContent>
          </Select>

          {/* Refresh Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw
              className={cn('mr-2 h-4 w-4', isRefreshing && 'animate-spin')}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* Map Container */}
      <div className="relative flex-1 overflow-hidden">
        <ReactLeafletMap
          machines={filteredMachines}
          onMarkerClick={setSelectedMachine}
          getMachineData={getMachineData}
        />

        {/* Filter Results Indicator */}
        {statusFilter !== 'all' && (
          <div className="absolute top-4 right-4 rounded-lg border bg-white px-3 py-2 shadow-lg">
            <div className="text-sm font-medium">
              Showing {filteredMachines.length} of {machines.length} machines
            </div>
            <div className="text-xs text-gray-500">
              Filter:{' '}
              {statusFilter === 'online' ? 'Online Only' : 'Offline Only'}
            </div>
            <button
              onClick={handleClearAllFilters}
              className="mt-1 text-xs text-blue-600 hover:underline"
            >
              Clear filter
            </button>
          </div>
        )}

        {/* Event Summary */}
        {totalEvents > 0 && statusFilter === 'all' && (
          <div className="absolute top-4 right-4 rounded-lg border bg-white px-3 py-2 shadow-lg">
            <div className="text-sm font-medium">
              {totalEvents} Events Detected
            </div>
            <div className="text-xs text-gray-500">
              {Object.keys(machineEventCounts).length} machines active
            </div>
          </div>
        )}

        {/* Enhanced Development Debug Info */}
        {process.env.NODE_ENV === 'development' && (
          <div className="absolute bottom-4 left-4 rounded-lg border bg-white px-3 py-2 text-xs shadow-lg">
            <div className="font-medium text-blue-600">🔧 Live Feed Debug</div>
            <div>Connection: {isConnected ? '✅' : '❌'}</div>
            <div>Topics: {mqttTopics.length}</div>
            <div>Machines: {machines.length}</div>
            <div>Filtered: {filteredMachines.length}</div>
            <div>Active: {Object.keys(machineEventCounts).length}</div>
            <div>Events: {totalEvents}</div>
            <div>
              Pulsating:{' '}
              {Object.values(pulsatingMachines).filter(Boolean).length}
            </div>
            <div>Processed: {processedEventKeysRef.current.size}</div>
            <div>Global: {globalProcessedEvents.size}</div>
            <div className="mt-1 text-blue-600">
              Audio: Handled by Alert System
            </div>
          </div>
        )}
      </div>

      {/* Machine Detail Modal */}
      <MachineDetailModal
        selectedMachine={selectedMachine}
        setSelectedMachine={setSelectedMachine}
        getMachineData={getMachineData}
        token={token}
        liveEvents={liveEventsForModal}
        isConnected={isConnected}
        mqttError={mqttError}
      />
    </div>
  );
}
