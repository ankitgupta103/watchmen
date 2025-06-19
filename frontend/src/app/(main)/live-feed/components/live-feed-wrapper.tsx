'use client';

import 'leaflet/dist/leaflet.css';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import useAllMachineStats from '@/hooks/use-all-machine-stats';
import useOrganization from '@/hooks/use-organization';
import { usePubSub } from '@/hooks/use-pub-sub';
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

import { Machine } from '@/lib/types/machine';
import { cn } from '@/lib/utils';

import MachineDetailModal from './machine-detail-modal';

interface LiveFeedWrapperProps {
  machines: Machine[];
  selectedDate?: Date;
}

const ReactLeafletMap = dynamic(() => import('./react-leaflet-map'), {
  ssr: false,
});

interface EventMessage {
  image_c_key: string;
  image_f_key: string;
  eventstr: string;
  event_severity: number;
  meta: {
    node_id: string;
    hb_count: string;
    last_hb_time: string;
    photos_taken: string;
    events_seen: string;
  };
}

interface MachineEvent {
  id: string;
  timestamp: Date;
  eventstr: string;
  image_c_key?: string;
  image_f_key?: string;
  cropped_image_url?: string;
  full_image_url?: string;
  images_loaded?: boolean;
  event_severity?: string;
}

interface SimpleMachineData {
  machine_id: number;
  events: MachineEvent[];
  event_count: number;
  last_event?: MachineEvent;
  last_updated: string;
  // Status and location from useMachineStats
  is_online: boolean;
  location: { lat: number; lng: number; timestamp: string };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  stats_data: any;
  buffer_size: number;
  // Add pulsating state for recent events
  is_pulsating: boolean;
  is_critical: boolean;
}

export default function LiveFeedWrapper({
  machines,
  selectedDate,
}: LiveFeedWrapperProps) {
  const { organizationId } = useOrganization();
  const [selectedMachine, setSelectedMachine] = useState<Machine | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all'); // Add status filter state

  // Track MQTT events per machine
  const [machineEvents, setMachineEvents] = useState<
    Record<number, MachineEvent[]>
  >({});

  // Track event counts for color coding
  const [machineEventCounts, setMachineEventCounts] = useState<
    Record<number, number>
  >({});

  // Track machines that recently received events (for pulsating animation)
  const [pulsatingMachines, setPulsatingMachines] = useState<
    Record<number, boolean>
  >({});

  // Use the custom hook to get all machine stats for status and location
  const machineStats = useAllMachineStats(machines);

  // Create MQTT topics for all machines
  const mqttTopics = useMemo(() => {
    if (machines.length === 0) return [];
    return machines.map(
      (machine) => `${organizationId}/_all_/+/${machine.id}/_all_/EVENT/#`,
    );
  }, [organizationId, machines]);

  // Fetch images from Django API
  const fetchEventImages = async (imageKeys: {
    image_c_key: string;
    image_f_key: string;
  }) => {
    try {
      const response = await fetch('/event-images/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(imageKeys),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        return {
          croppedImageUrl: data.cropped_image_url,
          fullImageUrl: data.full_image_url,
        };
      } else {
        throw new Error(data.error || 'Failed to fetch images');
      }
    } catch (error) {
      console.error('Error fetching images:', error);
      return null;
    }
  };

  // MQTT message handler
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleMqttMessage = async (topic: string, data: any) => {
    try {
      // Extract machine ID from topic path
      // Topic format: organization_id/_all_/2025-06-17/machine_id/EVENT/#
      const topicParts = topic.split('/');
      console.log('topicParts', topicParts, topicParts[3]);
      const machineIdPart = topicParts[3];

      if (machineIdPart && machineIdPart !== '_all_') {
        const machineId = parseInt(machineIdPart);

        if (!isNaN(machineId)) {
          // Parse the event message
          const eventMessage: EventMessage = data;

          // Create event object
          const eventId = `event-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          const newEvent: MachineEvent = {
            id: eventId,
            timestamp: new Date(),
            eventstr: eventMessage.eventstr || '',
            image_c_key: eventMessage.image_c_key,
            image_f_key: eventMessage.image_f_key,
            event_severity: eventMessage.event_severity.toString(),
            images_loaded: false,
          };

          // Add event to machine events
          setMachineEvents((prev) => ({
            ...prev,
            [machineId]: [...(prev[machineId] || []), newEvent].slice(-50), // Keep last 50 events
          }));

          // Update event count (cap at 20 for color gradation)
          setMachineEventCounts((prev) => ({
            ...prev,
            [machineId]: Math.min((prev[machineId] || 0) + 1, 20),
          }));

          // Start pulsating animation for this machine
          console.log('pulsatingMachines', machineId);
          setPulsatingMachines((prev) => ({
            ...prev,
            [machineId]: true,
          }));

          // Stop pulsating after 30 seconds
          setTimeout(() => {
            setPulsatingMachines((prev) => ({
              ...prev,
              [machineId]: false,
            }));
          }, 30000);

          // Fetch images if available
          if (eventMessage.image_c_key && eventMessage.image_f_key) {
            try {
              const imageUrls = await fetchEventImages({
                image_c_key: eventMessage.image_c_key,
                image_f_key: eventMessage.image_f_key,
              });

              if (imageUrls) {
                // Update the event with image URLs
                setMachineEvents((prev) => ({
                  ...prev,
                  [machineId]: (prev[machineId] || []).map((event) =>
                    event.id === eventId
                      ? {
                          ...event,
                          cropped_image_url: imageUrls.croppedImageUrl,
                          full_image_url: imageUrls.fullImageUrl,
                          images_loaded: true,
                        }
                      : event,
                  ),
                }));
              }
            } catch (error) {
              console.error('Error fetching images:', error);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error processing MQTT message:', error, { topic, data });
    }
  };

  // Use the PubSub hook for MQTT connection
  const { isConnected, error: mqttError } = usePubSub(
    mqttTopics,
    handleMqttMessage,
    {
      autoReconnect: true,
      parseJson: true,
    },
  );

  // Log MQTT connection status changes
  useEffect(() => {
    if (isConnected) {
      console.log('MQTT Connected to topics:', mqttTopics);
    } else if (mqttError) {
      console.error('MQTT Error:', mqttError);
    }
  }, [isConnected, mqttError, mqttTopics]);

  // Helper to get machine data
  const getMachineData = useCallback(
    (machineId: number): SimpleMachineData => {
      console.log('machineId', machineId);
      const events = machineEvents[machineId] || [];
      const eventCount = machineEventCounts[machineId] || 0;
      const lastEvent = events[events.length - 1];
      const stats = machineStats[machineId];
      const is_critical = events.some((event) => event.event_severity == '3');
      console.log('is_critical', is_critical);

      // Parse last_location.timestamp as Date and check if within last hour
      const lastSeen = machines[machineId]?.last_location?.timestamp
        ? new Date(machines[machineId].last_location.timestamp)
        : null;
      const oneHourAgo = new Date(Date.now() - 1000 * 60 * 60);

      const isOnline = !!lastSeen && lastSeen > oneHourAgo;

      // Get location from stats data
      const location = {
        lat: stats?.data?.message?.location?.lat ?? 0,
        lng: stats?.data?.message?.location?.long ?? 0,
        timestamp: stats?.data?.message?.location?.timestamp ?? '',
      };

      // Check if machine is currently pulsating
      const isPulsating = pulsatingMachines[machineId] || false;

      return {
        machine_id: machineId,
        events: events,
        event_count: eventCount,
        last_event: lastEvent,
        last_updated:
          lastEvent?.timestamp.toISOString() || new Date().toISOString(),
        is_online: isOnline,
        location: location,
        stats_data: stats?.data,
        buffer_size: stats?.buffer ?? 0,
        is_pulsating: isPulsating,
        is_critical: is_critical,
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

  // Calculate total events across all machines
  const totalEvents = Object.values(machineEventCounts).reduce(
    (sum, count) => sum + count,
    0,
  );

  // Calculate online/offline counts using proper status logic
  const onlineCount = machines.filter((machine) => {
    const lastSeen = machine.last_location?.timestamp
      ? new Date(machine.last_location.timestamp)
      : null;
    const oneHourAgo = new Date(Date.now() - 1000 * 60 * 60);
    const isOnline = !!lastSeen && lastSeen > oneHourAgo;

    return isOnline;
  }).length;

  const offlineCount = machines.filter((machine) => {
    const lastSeen = machine.last_location?.timestamp
      ? new Date(machine.last_location.timestamp)
      : null;
    const oneHourAgo = new Date(Date.now() - 1000 * 60 * 60);
    const isOnline = !!lastSeen && lastSeen > oneHourAgo;

    return !isOnline;
  }).length;

  // Filter machines based on status filter
  const filteredMachines = useMemo(() => {
    if (statusFilter === 'all') {
      return machines;
    }

    return machines.filter((machine) => {
      // Use the same 1-hour logic as getMachineData
      const lastSeen = machine.last_location?.timestamp
        ? new Date(machine.last_location.timestamp)
        : null;
      const oneHourAgo = new Date(Date.now() - 1000 * 60 * 60);
      const isOnline = !!lastSeen && lastSeen > oneHourAgo;

      if (statusFilter === 'online') {
        return isOnline;
      } else if (statusFilter === 'offline') {
        return !isOnline;
      }

      return true;
    });
  }, [machines, statusFilter]);

  // Refresh function
  const handleRefresh = () => {
    setIsRefreshing(true);

    // Clear events and counts to force refresh
    setMachineEvents({});
    setMachineEventCounts({});
    setPulsatingMachines({});

    setTimeout(() => setIsRefreshing(false), 1500);
  };

  // Clear all filters
  const handleClearAllFilters = () => {
    setStatusFilter('all');
  };

  return (
    <div className="flex h-full w-full flex-col">
      {/* Simplified Map Controls */}
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

        {/* Development Debug Info */}
        {process.env.NODE_ENV === 'development' && totalEvents > 0 && (
          <div className="absolute bottom-4 left-4 rounded-lg border bg-white px-3 py-2 text-xs shadow-lg">
            <div className="font-medium">Debug Info:</div>
            <div>Total machines: {machines.length}</div>
            <div>Filtered machines: {filteredMachines.length}</div>
            <div>Filter: {statusFilter}</div>
            <div>Active machines: {Object.keys(machineEventCounts).length}</div>
            <div>Total events: {totalEvents}</div>
            <div>Topics: {mqttTopics.length}</div>
            <div>
              Pulsating:{' '}
              {Object.values(pulsatingMachines).filter(Boolean).length}
            </div>
          </div>
        )}
      </div>

      {/* Machine Detail Modal */}
      <MachineDetailModal
        selectedMachine={selectedMachine}
        setSelectedMachine={setSelectedMachine}
        getMachineData={getMachineData}
      />
    </div>
  );
}
