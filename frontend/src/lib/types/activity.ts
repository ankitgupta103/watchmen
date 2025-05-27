export type ActivityIntensity = 'none' | 'low' | 'medium' | 'high' | 'critical';

export type ActivityType = 'suspicious' | 'health' | 'offline';

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
  intensity: ActivityIntensity;
  events: Array<ActivityEvent>;
}
