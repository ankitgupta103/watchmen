import { Machine } from './types/machine';

// Helper function to generate random date within last N days
const randomDateWithinDays = (days: number): string => {
  const now = new Date();
  const randomTime = now.getTime() - Math.random() * days * 24 * 60 * 60 * 1000;
  return new Date(randomTime).toISOString();
};

// Helper function to generate random coordinates around a center point
const randomCoordinate = (center: number, range: number): number => {
  return center + (Math.random() - 0.5) * range;
};

export const mockMachines: Machine[] = [
  {
    id: 1,
    name: 'sentinel-alpha-01',
    type: 'perimeter_guard',
    location: {
      lat: randomCoordinate(12.9716, 0.1),
      lng: randomCoordinate(77.5946, 0.1),
    },
    data: {
      status: 'online',
      lastSeen: new Date().toISOString(),
      suspiciousEvents: [
        {
          timestamp: randomDateWithinDays(3),
          confidence: 0.89,
          type: 'human_detection',
          marked: 'noted',
        },
        {
          timestamp: randomDateWithinDays(7),
          confidence: 0.76,
          type: 'unusual_activity',
          marked: 'unreviewed',
        },
        {
          timestamp: randomDateWithinDays(12),
          confidence: 0.94,
          type: 'weapon_detection',
          marked: 'noted',
        },
      ],
      healthEvents: [
        {
          timestamp: randomDateWithinDays(2),
          type: 'low_battery',
          severity: 'medium',
        },
      ],
    },
  },
  {
    id: 2,
    name: 'watchman-beta-02',
    type: 'mobile_patrol',
    location: {
      lat: randomCoordinate(13.0827, 0.1), // North Bangalore
      lng: randomCoordinate(77.5946, 0.1),
    },
    data: {
      status: 'offline',
      lastSeen: randomDateWithinDays(1),
      suspiciousEvents: [
        {
          timestamp: randomDateWithinDays(1),
          confidence: 0.67,
          type: 'human_detection',
          marked: 'ignored',
        },
        {
          timestamp: randomDateWithinDays(5),
          confidence: 0.82,
          type: 'unusual_activity',
          marked: 'unreviewed',
        },
      ],
      healthEvents: [
        {
          timestamp: randomDateWithinDays(1),
          type: 'offline',
          severity: 'critical',
        },
        {
          timestamp: randomDateWithinDays(3),
          type: 'gps_failure',
          severity: 'high',
        },
      ],
    },
  },
  {
    id: 3,
    name: 'guardian-gamma-03',
    type: 'fixed_surveillance',
    location: {
      lat: randomCoordinate(12.8698, 0.1), // South Bangalore
      lng: randomCoordinate(77.6699, 0.1),
    },
    data: {
      status: 'online',
      lastSeen: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 minutes ago
      suspiciousEvents: [
        {
          timestamp: randomDateWithinDays(2),
          confidence: 0.91,
          type: 'weapon_detection',
          marked: 'noted',
        },
        {
          timestamp: randomDateWithinDays(4),
          confidence: 0.73,
          type: 'human_detection',
          marked: 'unreviewed',
        },
        {
          timestamp: randomDateWithinDays(6),
          confidence: 0.88,
          type: 'unusual_activity',
          marked: 'unreviewed',
        },
        {
          timestamp: randomDateWithinDays(10),
          confidence: 0.95,
          type: 'weapon_detection',
          marked: 'noted',
        },
      ],
      healthEvents: [],
    },
  },
  {
    id: 4,
    name: 'scout-delta-04',
    type: 'roving_sensor',
    location: {
      lat: randomCoordinate(12.9352, 0.1), // Central Bangalore
      lng: randomCoordinate(77.6245, 0.1),
    },
    data: {
      status: 'maintenance',
      lastSeen: randomDateWithinDays(2),
      suspiciousEvents: [
        {
          timestamp: randomDateWithinDays(8),
          confidence: 0.71,
          type: 'human_detection',
          marked: 'ignored',
        },
      ],
      healthEvents: [
        {
          timestamp: randomDateWithinDays(2),
          type: 'camera_failure',
          severity: 'high',
        },
        {
          timestamp: randomDateWithinDays(4),
          type: 'hardware_failure',
          severity: 'medium',
        },
      ],
    },
  },
  {
    id: 5,
    name: 'watcher-epsilon-05',
    type: 'perimeter_guard',
    location: {
      lat: randomCoordinate(13.0358, 0.1), // Yelahanka area
      lng: randomCoordinate(77.599, 0.1),
    },
    data: {
      status: 'online',
      lastSeen: new Date(Date.now() - 15 * 60 * 1000).toISOString(), // 15 minutes ago
      suspiciousEvents: [
        {
          timestamp: randomDateWithinDays(1),
          confidence: 0.84,
          type: 'unusual_activity',
          marked: 'unreviewed',
        },
        {
          timestamp: randomDateWithinDays(3),
          confidence: 0.92,
          type: 'human_detection',
          marked: 'noted',
        },
        {
          timestamp: randomDateWithinDays(5),
          confidence: 0.78,
          type: 'unusual_activity',
          marked: 'unreviewed',
        },
        {
          timestamp: randomDateWithinDays(9),
          confidence: 0.96,
          type: 'weapon_detection',
          marked: 'noted',
        },
        {
          timestamp: randomDateWithinDays(14),
          confidence: 0.69,
          type: 'human_detection',
          marked: 'ignored',
        },
      ],
      healthEvents: [
        {
          timestamp: randomDateWithinDays(7),
          type: 'low_battery',
          severity: 'low',
        },
      ],
    },
  },
  {
    id: 6,
    name: 'sentinel-zeta-06',
    type: 'mobile_patrol',
    location: {
      lat: randomCoordinate(12.8456, 0.1), // Banashankari area
      lng: randomCoordinate(77.5391, 0.1),
    },
    data: {
      status: 'offline',
      lastSeen: randomDateWithinDays(3),
      suspiciousEvents: [
        {
          timestamp: randomDateWithinDays(4),
          confidence: 0.87,
          type: 'weapon_detection',
          marked: 'unreviewed',
        },
        {
          timestamp: randomDateWithinDays(11),
          confidence: 0.74,
          type: 'human_detection',
          marked: 'noted',
        },
      ],
      healthEvents: [
        {
          timestamp: randomDateWithinDays(3),
          type: 'offline',
          severity: 'critical',
        },
        {
          timestamp: randomDateWithinDays(5),
          type: 'hardware_failure',
          severity: 'high',
        },
        {
          timestamp: randomDateWithinDays(8),
          type: 'camera_failure',
          severity: 'medium',
        },
      ],
    },
  },
  {
    id: 7,
    name: 'guardian-eta-07',
    type: 'fixed_surveillance',
    location: {
      lat: randomCoordinate(12.9698, 0.1), // Rajajinagar area
      lng: randomCoordinate(77.5587, 0.1),
    },
    data: {
      status: 'online',
      lastSeen: new Date(Date.now() - 2 * 60 * 1000).toISOString(), // 2 minutes ago
      suspiciousEvents: [
        {
          timestamp: randomDateWithinDays(1),
          confidence: 0.93,
          type: 'weapon_detection',
          marked: 'unreviewed',
        },
        {
          timestamp: randomDateWithinDays(2),
          confidence: 0.81,
          type: 'unusual_activity',
          marked: 'unreviewed',
        },
        {
          timestamp: randomDateWithinDays(6),
          confidence: 0.77,
          type: 'human_detection',
          marked: 'noted',
        },
      ],
      healthEvents: [],
    },
  },
  {
    id: 8,
    name: 'patrol-theta-08',
    type: 'roving_sensor',
    location: {
      lat: randomCoordinate(12.9279, 0.1), // Indiranagar area
      lng: randomCoordinate(77.6413, 0.1),
    },
    data: {
      status: 'online',
      lastSeen: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
      suspiciousEvents: [
        {
          timestamp: randomDateWithinDays(7),
          confidence: 0.85,
          type: 'human_detection',
          marked: 'ignored',
        },
        {
          timestamp: randomDateWithinDays(13),
          confidence: 0.72,
          type: 'unusual_activity',
          marked: 'unreviewed',
        },
      ],
      healthEvents: [
        {
          timestamp: randomDateWithinDays(1),
          type: 'low_battery',
          severity: 'medium',
        },
        {
          timestamp: randomDateWithinDays(10),
          type: 'gps_failure',
          severity: 'low',
        },
      ],
    },
  },
  {
    id: 9,
    name: 'lookout-iota-09',
    type: 'perimeter_guard',
    location: {
      lat: randomCoordinate(12.9034, 0.1), // Koramangala area
      lng: randomCoordinate(77.6146, 0.1),
    },
    data: {
      status: 'maintenance',
      lastSeen: randomDateWithinDays(1),
      suspiciousEvents: [
        {
          timestamp: randomDateWithinDays(2),
          confidence: 0.89,
          type: 'weapon_detection',
          marked: 'noted',
        },
        {
          timestamp: randomDateWithinDays(8),
          confidence: 0.76,
          type: 'human_detection',
          marked: 'unreviewed',
        },
        {
          timestamp: randomDateWithinDays(15),
          confidence: 0.91,
          type: 'unusual_activity',
          marked: 'noted',
        },
      ],
      healthEvents: [
        {
          timestamp: randomDateWithinDays(1),
          type: 'camera_failure',
          severity: 'critical',
        },
        {
          timestamp: randomDateWithinDays(3),
          type: 'hardware_failure',
          severity: 'high',
        },
      ],
    },
  },
  {
    id: 10,
    name: 'sentry-kappa-10',
    type: 'mobile_patrol',
    location: {
      lat: randomCoordinate(13.0097, 0.1), // Hebbal area
      lng: randomCoordinate(77.5963, 0.1),
    },
    data: {
      status: 'online',
      lastSeen: new Date(Date.now() - 10 * 60 * 1000).toISOString(), // 10 minutes ago
      suspiciousEvents: [
        {
          timestamp: randomDateWithinDays(3),
          confidence: 0.88,
          type: 'unusual_activity',
          marked: 'unreviewed',
        },
        {
          timestamp: randomDateWithinDays(6),
          confidence: 0.94,
          type: 'weapon_detection',
          marked: 'noted',
        },
        {
          timestamp: randomDateWithinDays(9),
          confidence: 0.71,
          type: 'human_detection',
          marked: 'ignored',
        },
        {
          timestamp: randomDateWithinDays(12),
          confidence: 0.83,
          type: 'unusual_activity',
          marked: 'unreviewed',
        },
      ],
      healthEvents: [
        {
          timestamp: randomDateWithinDays(5),
          type: 'low_battery',
          severity: 'low',
        },
      ],
    },
  },
  {
    id: 11,
    name: 'observer-lambda-11',
    type: 'fixed_surveillance',
    location: {
      lat: randomCoordinate(12.8031, 0.1), // Electronic City area
      lng: randomCoordinate(77.6593, 0.1),
    },
    data: {
      status: 'offline',
      lastSeen: randomDateWithinDays(5),
      suspiciousEvents: [
        {
          timestamp: randomDateWithinDays(6),
          confidence: 0.79,
          type: 'human_detection',
          marked: 'noted',
        },
        {
          timestamp: randomDateWithinDays(14),
          confidence: 0.86,
          type: 'weapon_detection',
          marked: 'unreviewed',
        },
      ],
      healthEvents: [
        {
          timestamp: randomDateWithinDays(5),
          type: 'offline',
          severity: 'critical',
        },
        {
          timestamp: randomDateWithinDays(7),
          type: 'hardware_failure',
          severity: 'critical',
        },
        {
          timestamp: randomDateWithinDays(12),
          type: 'gps_failure',
          severity: 'high',
        },
      ],
    },
  },
  {
    id: 12,
    name: 'vigilant-mu-12',
    type: 'roving_sensor',
    location: {
      lat: randomCoordinate(12.9719, 0.1), // Malleshwaram area
      lng: randomCoordinate(77.5737, 0.1),
    },
    data: {
      status: 'online',
      lastSeen: new Date(Date.now() - 45 * 60 * 1000).toISOString(), // 45 minutes ago
      suspiciousEvents: [
        {
          timestamp: randomDateWithinDays(1),
          confidence: 0.92,
          type: 'weapon_detection',
          marked: 'unreviewed',
        },
        {
          timestamp: randomDateWithinDays(4),
          confidence: 0.75,
          type: 'unusual_activity',
          marked: 'unreviewed',
        },
        {
          timestamp: randomDateWithinDays(7),
          confidence: 0.87,
          type: 'human_detection',
          marked: 'noted',
        },
        {
          timestamp: randomDateWithinDays(11),
          confidence: 0.73,
          type: 'unusual_activity',
          marked: 'ignored',
        },
        {
          timestamp: randomDateWithinDays(16),
          confidence: 0.9,
          type: 'weapon_detection',
          marked: 'noted',
        },
      ],
      healthEvents: [
        {
          timestamp: randomDateWithinDays(2),
          type: 'camera_failure',
          severity: 'medium',
        },
        {
          timestamp: randomDateWithinDays(9),
          type: 'low_battery',
          severity: 'low',
        },
      ],
    },
  },
];

// Usage example:
// const machines = mockMachines;
// console.log(`Generated ${machines.length} mock machines`);
// console.log(`Total suspicious events: ${machines.reduce((sum, m) => sum + (m.data.suspiciousEvents?.length || 0), 0)}`);
// console.log(`Total health events: ${machines.reduce((sum, m) => sum + (m.data.healthEvents?.length || 0), 0)}`);

// Export specific subsets for different testing scenarios
export const onlineMachines = mockMachines.filter(
  (m) => m.data.status === 'online',
);
export const offlineMachines = mockMachines.filter(
  (m) => m.data.status === 'offline',
);
export const maintenanceMachines = mockMachines.filter(
  (m) => m.data.status === 'maintenance',
);

export const highActivityMachines = mockMachines.filter(
  (m) =>
    (m.data.suspiciousEvents?.length || 0) +
      (m.data.healthEvents?.length || 0) >
    3,
);

export const criticalMachines = mockMachines.filter(
  (m) =>
    m.data.healthEvents?.some((e) => e.severity === 'critical') ||
    m.data.status === 'offline',
);
