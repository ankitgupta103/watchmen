'use client';

import { useCallback, useEffect, useState } from 'react';

import {
  HealthEventSeverity,
  HealthEventType,
  MachineData,
  SuspiciousEventMarked,
  SuspiciousEventType,
} from '@/lib/types/machine';

// Helper function to generate random date within last N days
const randomDateWithinDays = (days: number): string => {
  const now = new Date();
  const randomTime = now.getTime() - Math.random() * days * 24 * 60 * 60 * 1000;
  return new Date(randomTime).toISOString();
};

// Generate random suspicious event
const generateRandomSuspiciousEvent = () => {
  const types: SuspiciousEventType[] = [
    'human_detection',
    'weapon_detection',
    'unusual_activity',
  ];
  const marked: SuspiciousEventMarked[] = ['ignored', 'noted', 'unreviewed'];

  return {
    url: Math.random() > 0.6 ? 'https://picsum.photos/600/400' : undefined,
    timestamp: randomDateWithinDays(Math.random() * 30), // Random within 30 days
    confidence: 0.6 + Math.random() * 0.4, // 0.6 to 1.0
    type: types[Math.floor(Math.random() * types.length)],
    marked: marked[Math.floor(Math.random() * marked.length)],
  };
};

// Generate random health event
const generateRandomHealthEvent = () => {
  const types: HealthEventType[] = [
    'offline',
    'hardware_failure',
    'low_battery',
    'gps_failure',
    'camera_failure',
  ];
  const severities: HealthEventSeverity[] = [
    'low',
    'medium',
    'high',
    'critical',
  ];

  return {
    timestamp: randomDateWithinDays(Math.random() * 14), // Random within 14 days
    type: types[Math.floor(Math.random() * types.length)],
    severity: severities[Math.floor(Math.random() * severities.length)],
  };
};

// Initial dummy data generator
const generateInitialMachineData = (machineId: number): MachineData => {
  console.log('Generating initial machine data for machineId:', machineId);
  const statuses = ['online', 'offline', 'maintenance'];
  const status = statuses[Math.floor(Math.random() * statuses.length)];

  // Generate 0-8 suspicious events
  const suspiciousEvents = Array.from(
    { length: Math.floor(Math.random() * 9) },
    generateRandomSuspiciousEvent,
  );

  // Generate 0-5 health events, more likely if offline/maintenance
  const healthEventCount =
    status === 'online'
      ? Math.floor(Math.random() * 3)
      : Math.floor(Math.random() * 5) + 1;

  const healthEvents = Array.from(
    { length: healthEventCount },
    generateRandomHealthEvent,
  );

  // If status is offline, ensure there's an offline health event
  if (status === 'offline' && !healthEvents.some((e) => e.type === 'offline')) {
    healthEvents.push({
      timestamp: randomDateWithinDays(Math.random() * 7),
      type: 'offline',
      severity: 'critical',
    });
  }

  const lastSeenOffset =
    status === 'online'
      ? Math.random() * 60 * 60 * 1000 // 0-60 minutes ago
      : Math.random() * 7 * 24 * 60 * 60 * 1000; // 0-7 days ago

  return {
    status,
    lastSeen: new Date(Date.now() - lastSeenOffset).toISOString(),
    suspiciousEvents,
    healthEvents,
  };
};

export function useLiveMachineData(
  machineIds: number[],
  enableLiveUpdates: boolean = true,
) {
  const [machineDataMap, setMachineDataMap] = useState<
    Map<number, MachineData>
  >(new Map());
  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date());

  // Initialize data for all machines
  useEffect(() => {
    const initialMap = new Map<number, MachineData>();
    machineIds.forEach((id) => {
      initialMap.set(id, generateInitialMachineData(id));
    });
    setMachineDataMap(initialMap);
  }, [machineIds]);

  // Simulate live updates
  useEffect(() => {
    if (!enableLiveUpdates || machineIds.length === 0) return;

    const updateInterval = setInterval(() => {
      setMachineDataMap((currentMap) => {
        const newMap = new Map(currentMap);

        // Randomly pick 1-3 machines to update
        const machinesToUpdate = [...machineIds]
          .sort(() => Math.random() - 0.5)
          .slice(0, Math.floor(Math.random() * 3) + 1);

        machinesToUpdate.forEach((machineId) => {
          const currentData = newMap.get(machineId);
          if (!currentData) return;

          const updatedData = { ...currentData };

          // 20% chance to change status
          if (Math.random() < 0.2) {
            const statuses = ['online', 'offline', 'maintenance'];
            const newStatus =
              statuses[Math.floor(Math.random() * statuses.length)];
            updatedData.status = newStatus;

            // Update lastSeen based on new status
            if (newStatus === 'online') {
              updatedData.lastSeen = new Date().toISOString();
            } else if (newStatus === 'offline') {
              // Add offline health event if switching to offline
              updatedData.healthEvents = [
                {
                  timestamp: new Date().toISOString(),
                  type: 'offline',
                  severity: 'critical',
                },
                ...(updatedData?.healthEvents ?? []),
              ];
            }
          }

          // Update lastSeen for online machines
          if (updatedData.status === 'online') {
            updatedData.lastSeen = new Date().toISOString();
          }

          // 15% chance to add new suspicious event
          if (Math.random() < 0.15) {
            const newEvent = generateRandomSuspiciousEvent();
            newEvent.timestamp = new Date().toISOString();
            newEvent.marked = 'unreviewed'; // New events are unreviewed
            updatedData.suspiciousEvents = [
              newEvent,
              ...(updatedData?.suspiciousEvents ?? []),
            ].slice(0, 20); // Keep max 20
          }

          // 10% chance to add new health event
          if (Math.random() < 0.1) {
            const newEvent = generateRandomHealthEvent();
            newEvent.timestamp = new Date().toISOString();
            updatedData.healthEvents = [
              newEvent,
              ...(updatedData?.healthEvents ?? []),
            ].slice(0, 15); // Keep max 15
          }

          // 5% chance to mark some unreviewed events as reviewed
          if (Math.random() < 0.05) {
            updatedData.suspiciousEvents = updatedData?.suspiciousEvents?.map(
              (event) => {
                if (event.marked === 'unreviewed' && Math.random() < 0.3) {
                  return {
                    ...event,
                    marked: Math.random() < 0.7 ? 'noted' : 'ignored',
                  };
                }
                return event;
              },
            );
          }

          newMap.set(machineId, updatedData);
        });

        return newMap;
      });

      setLastUpdateTime(new Date());
    }, 5000); // Update every 5 seconds

    return () => clearInterval(updateInterval);
  }, [machineIds, enableLiveUpdates]);

  // Get data for a specific machine
  const getMachineData = useCallback(
    (machineId: number): MachineData => {
      return (
        machineDataMap.get(machineId) || {
          status: 'offline',
          lastSeen: new Date().toISOString(),
          suspiciousEvents: [],
          healthEvents: [],
        }
      );
    },
    [machineDataMap],
  );

  // Get all machine data
  const getAllMachineData = useCallback((): Record<number, MachineData> => {
    const result: Record<number, MachineData> = {};
    machineDataMap.forEach((data, id) => {
      result[id] = data;
    });
    return result;
  }, [machineDataMap]);

  // Manually update a machine's suspicious event status
  const updateSuspiciousEventStatus = useCallback(
    (
      machineId: number,
      eventIndex: number,
      newStatus: SuspiciousEventMarked,
    ) => {
      setMachineDataMap((currentMap) => {
        const newMap = new Map(currentMap);
        const machineData = newMap.get(machineId);

        if (machineData && machineData.suspiciousEvents?.[eventIndex]) {
          const updatedData = { ...machineData };
          updatedData.suspiciousEvents = [
            ...(updatedData?.suspiciousEvents ?? []),
          ];
          updatedData.suspiciousEvents[eventIndex] = {
            ...updatedData.suspiciousEvents[eventIndex],
            marked: newStatus,
          };
          newMap.set(machineId, updatedData);
        }

        return newMap;
      });
    },
    [],
  );

  // Force refresh data for a machine
  const refreshMachineData = useCallback((machineId: number) => {
    setMachineDataMap((currentMap) => {
      const newMap = new Map(currentMap);
      newMap.set(machineId, generateInitialMachineData(machineId));
      return newMap;
    });
  }, []);

  return {
    getMachineData,
    getAllMachineData,
    updateSuspiciousEventStatus,
    refreshMachineData,
    lastUpdateTime,
    isConnected: enableLiveUpdates, // Simulate connection status
  };
}
