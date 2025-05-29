export type ActivityIntensity = 'none' | 'low' | 'medium' | 'high' | 'critical';

export type ActivityType = 'suspicious' | 'health' | 'offline' | 'unknown';

export type ActivityEvent = {
  machineId: number;
  machineName: string;
  type: ActivityType;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  details: any;
};

export interface DayActivity {
  date: Date;
  suspiciousCount: number;
  healthIssues: number;
  offlineCount: number;
  unknownCount: number;
  intensity: ActivityIntensity;
  events: Array<ActivityEvent>;
}
