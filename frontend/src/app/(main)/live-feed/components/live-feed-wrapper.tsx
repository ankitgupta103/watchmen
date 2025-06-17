'use client';

import 'leaflet/dist/leaflet.css';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useMachineStats } from '@/hooks/use-machine-stats';
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

import MachineDetailModal from './machine-detail-model';

interface LiveFeedWrapperProps {
  machines: Machine[];
  selectedDate?: Date;
}

const ReactLeafletMap = dynamic(() => import('./react-leaflet-map'), {
  ssr: false,
});

// Health status constants
const HEALTH_STATUS = {
  HEALTHY: 1,
  OFFLINE: 2,
  MAINTENANCE: 3,
} as const;

// Custom hook to collect all machine stats by calling useMachineStats for each machine at the top level
function useAllMachineStats(machines: Machine[]) {
  // This will force all useMachineStats hooks to be called in the same order every render
  // eslint-disable-next-line
  const stats: Record<number, { buffer: number; data: any | null }> = {};
  for (let i = 0; i < machines.length; i++) {
    const machine = machines[i];
    // eslint-disable-next-line react-hooks/rules-of-hooks
    stats[machine.id] = useMachineStats(machine.id);
  }
  return stats;
}

export default function LiveFeedWrapper({
  machines,
  selectedDate,
}: LiveFeedWrapperProps) {
  const { organizationId } = useOrganization();
  const [selectedMachine, setSelectedMachine] = useState<Machine | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [activityFilter, setActivityFilter] = useState<string>('all');
  const [isRefreshing, setIsRefreshing] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [liveData, setLiveData] = useState<Record<number, any>>({});
  
  // New state for tracking MQTT events per machine
  const [machineEvents, setMachineEvents] = useState<Record<number, Array<{
    id: string;
    timestamp: Date;
    eventstr: string;
    image_c_key?: string;
    image_f_key?: string;
    cropped_image_url?: string;
    full_image_url?: string;
    images_loaded?: boolean;
  }>>>({});
  
  // Track event counts for visual indicators
  const [machineEventCounts, setMachineEventCounts] = useState<Record<number, number>>({});

  // Use the custom hook to get all machine stats
  const machineStats = useAllMachineStats(machines);

  // Create MQTT topic for live data
  const mqttTopics = useMemo(() => {
    const currentDate = selectedDate
      ? selectedDate.toISOString().split('T')[0]
      : new Date().toISOString().split('T')[0]; // Format: YYYY-MM-DD

    return [`${organizationId}/_all_/${currentDate}/+/_all_/EVENT/#`];
  }, [organizationId, selectedDate]);

  // MQTT message handler
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleMqttMessage = useCallback(async (topic: string, data: any) => {
    try {
      // Extract machine ID from topic path
      // Topic format: organization_id/_all_/2025-06-17/machine_id/_all_/EVENT/#
      const topicParts = topic.split('/');
      const dateIndex = topicParts.findIndex((part) => part.match(/\d{4}-\d{2}-\d{2}/));
      const machineIdPart = topicParts[dateIndex + 1];

      if (machineIdPart && machineIdPart !== '_all_') {
        const machineId = parseInt(machineIdPart);

        if (!isNaN(machineId)) {
          // Create event object
          const eventId = `event-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          const newEvent = {
            id: eventId,
            timestamp: new Date(),
            eventstr: data.eventstr || '',
            image_c_key: data.image_c_key,
            image_f_key: data.image_f_key,
            images_loaded: false,
          };

          // Add event to machine events
          setMachineEvents((prev) => ({
            ...prev,
            [machineId]: [...(prev[machineId] || []), newEvent].slice(-50), // Keep last 50 events
          }));

          // Update event count
          setMachineEventCounts((prev) => ({
            ...prev,
            [machineId]: Math.min((prev[machineId] || 0) + 1, 9), // Cap at 9 for display
          }));

          // Update live data
          setLiveData((prev) => ({
            ...prev,
            [machineId]: {
              ...data,
              timestamp: new Date().toISOString(),
              topic: topic,
              last_event: newEvent,
            },
          }));

          // Trigger alert sound
          if (window.dispatchEvent) {
            window.dispatchEvent(new CustomEvent('mqtt-event-received', {
              detail: {
                machineId,
                event: newEvent,
                topic,
              }
            }));
          }

          // Fetch images from Django API
          if (data.image_c_key && data.image_f_key) {
            try {
              const response = await fetch('/api/event-images/', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  image_c_key: data.image_c_key,
                  image_f_key: data.image_f_key,
                }),
              });

              if (response.ok) {
                const imageData = await response.json();
                
                // Update the event with image URLs
                setMachineEvents((prev) => ({
                  ...prev,
                  [machineId]: (prev[machineId] || []).map(event => 
                    event.id === eventId 
                      ? {
                          ...event,
                          cropped_image_url: imageData.cropped_image_url,
                          full_image_url: imageData.full_image_url,
                          images_loaded: true,
                        }
                      : event
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
  }, []);

  // Use the PubSub hook for MQTT connection
  const {
    isConnected,
    error: mqttError,
    getCurrentMessage,
    subscriptionStats,
  } = usePubSub(mqttTopics, handleMqttMessage, {
    autoReconnect: true,
    parseJson: true,
  });

  // Log MQTT connection status changes
  useEffect(() => {
    if (isConnected) {
      console.log('MQTT Connected to topics:', mqttTopics);
    } else if (mqttError) {
      console.error('MQTT Error:', mqttError);
    }
  }, [isConnected, mqttError, mqttTopics]);

  // Helper to get event count for a machine
  const getEventCount = (machineId: number): number => {
    return machineEventCounts[machineId] || 0;
  };

  // Helper to get events for a machine
  const getMachineEvents = (machineId: number) => {
    return machineEvents[machineId] || [];
  };

  // Helper to get health status from stats and live data
  const getHealthStatus = (machineId: number): number => {
    const stats = machineStats[machineId];
    const live = liveData[machineId];

    // Priority: live data > stats data
    if (live?.health_status && typeof live.health_status === 'number') {
      return live.health_status;
    }

    if (
      stats?.data?.message?.health_status &&
      typeof stats.data.message.health_status === 'number'
    ) {
      return stats.data.message.health_status;
    }

    // Fallback: if no data at all, consider offline
    if (!stats?.data && !live) {
      return HEALTH_STATUS.OFFLINE;
    }

    // If we have data but no explicit health status, assume healthy
    return HEALTH_STATUS.HEALTHY;
  };

  // Helper to get status string from health status
  const getStatus = (machineId: number): string => {
    const healthStatus = getHealthStatus(machineId);

    switch (healthStatus) {
      case HEALTH_STATUS.HEALTHY:
        return 'online';
      case HEALTH_STATUS.OFFLINE:
        return 'offline';
      case HEALTH_STATUS.MAINTENANCE:
        return 'maintenance';
      default:
        return 'offline';
    }
  };

  // Helper to get lat/lng from stats and live data
  const getLatLng = (machineId: number) => {
    const stats = machineStats[machineId];
    const live = liveData[machineId];

    // Priority: live data > stats data
    let lat, lng;

    if (live?.location) {
      lat = live.location.lat;
      lng = live.location.lng;
    } else if (live?.lat && live?.lng) {
      // Handle flat structure
      lat = live.lat;
      lng = live.lng;
    } else if (stats?.data?.message?.location) {
      lat = stats.data.message.location.lat;
      lng = stats.data.message.location.lng;
    }

    return {
      lat: typeof lat === 'number' ? lat : 0,
      lng: typeof lng === 'number' ? lng : 0,
    };
  };

  // Helper to get MachineData for a machine (combining stats and live data)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getMachineData = (machineId: number): any => {
    const stats = machineStats[machineId];
    const live = liveData[machineId];
    const events = getMachineEvents(machineId);
    const eventCount = getEventCount(machineId);

    // Merge stats and live data, with live data taking priority
    const baseData = stats?.data?.message || {};
    const liveUpdate = live || {};

    return {
      ...baseData,
      ...liveUpdate,
      machine_id: machineId,
      health_status: getHealthStatus(machineId),
      status: getStatus(machineId),
      location: getLatLng(machineId),
      last_updated:
        live?.timestamp || baseData.timestamp || new Date().toISOString(),
      is_live: !!live,
      events: events,
      event_count: eventCount,
      last_event: live?.last_event,
    };
  };

  // Filter machines based on selected filters and current status
  const filteredMachines = useMemo(() => {
    return machines.filter((machine) => {
      const status = getStatus(machine.id);
      if (statusFilter !== 'all' && status !== statusFilter) {
        return false;
      }

      // Activity filter logic based on live data
      if (activityFilter !== 'all') {
        const live = liveData[machine.id];

        if (activityFilter === 'high') {
          // High activity: received live data in last 5 minutes
          if (live?.timestamp) {
            const lastUpdate = new Date(live.timestamp);
            const now = new Date();
            const diffMinutes =
              (now.getTime() - lastUpdate.getTime()) / (1000 * 60);
            return diffMinutes <= 5;
          }
          return false;
        } else if (activityFilter === 'medium') {
          // Medium activity: received live data in last 30 minutes
          if (live?.timestamp) {
            const lastUpdate = new Date(live.timestamp);
            const now = new Date();
            const diffMinutes =
              (now.getTime() - lastUpdate.getTime()) / (1000 * 60);
            return diffMinutes <= 30 && diffMinutes > 5;
          }
          return false;
        } else if (activityFilter === 'low') {
          // Low activity: no recent live data or older than 30 minutes
          if (live?.timestamp) {
            const lastUpdate = new Date(live.timestamp);
            const now = new Date();
            const diffMinutes =
              (now.getTime() - lastUpdate.getTime()) / (1000 * 60);
            return diffMinutes > 30;
          }
          return true; // No live data = low activity
        }
      }

      return true;
    });
  }, [machines, statusFilter, activityFilter, machineStats, liveData]);

  // Calculate counts using current health status
  const onlineCount = machines.filter(
    (machine) => getStatus(machine.id) === 'online',
  ).length;
  const offlineCount = machines.filter(
    (machine) => getStatus(machine.id) === 'offline',
  ).length;
  const maintenanceCount = machines.filter(
    (machine) => getStatus(machine.id) === 'maintenance',
  ).length;

  // Calculate alerts based on machine data
  const totalAlerts = machines.filter((machine) => {
    const machineData = getMachineData(machine.id);
    // Add your alert logic here based on your requirements
    return (
      machineData.alert_status === true ||
      machineData.error_count > 0 ||
      machineData.warning_count > 0 ||
      machineData.health_status === HEALTH_STATUS.MAINTENANCE
    );
  }).length;

  // Refresh function
  const handleRefresh = () => {
    setIsRefreshing(true);

    // Clear live data and events to force refresh from current topic data
    setLiveData({});
    setMachineEvents({});
    setMachineEventCounts({});

    // Process any current messages from PubSub
    mqttTopics.forEach((topic) => {
      const currentMessage = getCurrentMessage(topic);
      if (currentMessage) {
        handleMqttMessage(topic, currentMessage.data);
      }
    });

    setTimeout(() => setIsRefreshing(false), 1500);
  };

  return (
    <div className="flex h-full w-full flex-col">
      {/* Enhanced Map Controls */}
      <div className="flex items-center justify-between border-b bg-white p-4 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-600" />
            <span className="font-semibold">Network Overview</span>

            {/* MQTT Connection Status */}
            <div className="flex items-center gap-1 text-xs">
              <div
                className={cn(
                  'h-2 w-2 rounded-full',
                  isConnected ? 'bg-green-500' : 'bg-red-500',
                )}
              ></div>
              <span className="text-gray-500">
                {isConnected ? 'Live' : 'Offline'}
              </span>
              {Object.keys(liveData).length > 0 && (
                <span className="ml-1 text-gray-400">
                  ({Object.keys(liveData).length} active)
                </span>
              )}
            </div>

            {/* Show MQTT error if any */}
            {mqttError && (
              <div className="text-xs text-red-500" title={mqttError.message}>
                Connection Error
              </div>
            )}
          </div>

          {/* Quick Stats */}
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <span>{onlineCount} Online</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-red-500"></div>
              <span>{offlineCount} Offline</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-yellow-500"></div>
              <span>{maintenanceCount} Maintenance</span>
            </div>
            {totalAlerts > 0 && (
              <Badge variant="destructive" className="text-xs">
                {totalAlerts} Alert{totalAlerts > 1 ? 's' : ''}
              </Badge>
            )}
            {Object.values(machineEventCounts).reduce((sum, count) => sum + count, 0) > 0 && (
              <Badge variant="outline" className="text-xs border-orange-300 text-orange-700">
                {Object.values(machineEventCounts).reduce((sum, count) => sum + count, 0)} Event{Object.values(machineEventCounts).reduce((sum, count) => sum + count, 0) > 1 ? 's' : ''}
              </Badge>
            )}
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
              <SelectItem value="online">Online</SelectItem>
              <SelectItem value="offline">Offline</SelectItem>
              <SelectItem value="maintenance">Maintenance</SelectItem>
            </SelectContent>
          </Select>

          {/* Activity Filter */}
          <Select value={activityFilter} onValueChange={setActivityFilter}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="All Activity" />
            </SelectTrigger>
            <SelectContent className="z-[1000]">
              <SelectItem value="all">All Activity</SelectItem>
              <SelectItem value="high">High Activity</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low Activity</SelectItem>
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
          machines={filteredMachines.map((machine) => ({
            ...machine,
            last_location: getLatLng(machine.id),
          }))}
          onMarkerClick={setSelectedMachine}
          selectedDate={selectedDate}
          getMachineData={getMachineData}
        />

        {/* Filtered Results Indicator */}
        {filteredMachines.length !== machines.length && (
          <div className="absolute top-4 right-4 rounded-lg border bg-white px-3 py-2 shadow-lg">
            <div className="text-sm font-medium">
              Showing {filteredMachines.length} of {machines.length} machines
            </div>
            {(statusFilter !== 'all' || activityFilter !== 'all') && (
              <button
                onClick={() => {
                  setStatusFilter('all');
                  setActivityFilter('all');
                }}
                className="mt-1 text-xs text-blue-600 hover:underline"
              >
                Clear filters
              </button>
            )}
          </div>
        )}

        {/* Live Data Debug Info (remove in production) */}
        {process.env.NODE_ENV === 'development' &&
          (Object.keys(liveData).length > 0 || Object.keys(machineEvents).length > 0) && (
            <div className="absolute bottom-4 left-4 rounded-lg border bg-white px-3 py-2 text-xs shadow-lg">
              <div className="font-medium">Live Data Debug:</div>
              <div>{Object.keys(liveData).length} machines with live data</div>
              <div>{Object.keys(machineEvents).length} machines with events</div>
              <div>Total events: {Object.values(machineEventCounts).reduce((sum, count) => sum + count, 0)}</div>
              <div>Topics: {Object.keys(subscriptionStats).length}</div>
            </div>
          )}
      </div>

      {/* Enhanced Machine Detail Modal */}
      <MachineDetailModal
        selectedMachine={selectedMachine}
        setSelectedMachine={setSelectedMachine}
        getMachineData={getMachineData}
      />
    </div>
  );
}