'use client';

import React, { useMemo, useState } from 'react';
import { Activity, ChevronLeft, ChevronRight, MapPin } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

import { DayActivity } from '@/lib/types/activity';
import { Machine } from '@/lib/types/machine';
import { cn } from '@/lib/utils';

interface HeatMapCalendarProps {
  machines: Machine[];
}

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export default function HeatMapCalendar({ machines }: HeatMapCalendarProps) {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(
    new Date(),
  );
  const [currentMonth, setCurrentMonth] = useState(new Date());

  // Process machine data to create heat map data
  const heatMapData = useMemo(() => {
    const activityMap = new Map<string, DayActivity>();

    machines.forEach((machine) => {
      // Process suspicious events
      machine.data.suspiciousEvents?.forEach((event) => {
        const date = new Date(event.timestamp);
        const dateKey = date.toDateString();

        if (!activityMap.has(dateKey)) {
          activityMap.set(dateKey, {
            date,
            suspiciousCount: 0,
            healthIssues: 0,
            offlineCount: 0,
            intensity: 'none',
            events: [],
          });
        }

        const dayActivity = activityMap.get(dateKey)!;
        dayActivity.suspiciousCount++;
        dayActivity.events.push({
          machineId: machine.id,
          machineName: machine.name,
          type: 'suspicious',
          details: event,
        });
      });

      // Process health events
      machine.data.healthEvents?.forEach((event) => {
        const date = new Date(event.timestamp);
        const dateKey = date.toDateString();

        if (!activityMap.has(dateKey)) {
          activityMap.set(dateKey, {
            date,
            suspiciousCount: 0,
            healthIssues: 0,
            offlineCount: 0,
            intensity: 'none',
            events: [],
          });
        }

        const dayActivity = activityMap.get(dateKey)!;
        dayActivity.healthIssues++;
        if (event.type === 'offline') dayActivity.offlineCount++;

        dayActivity.events.push({
          machineId: machine.id,
          machineName: machine.name,
          type: 'health',
          details: event,
        });
      });
    });

    // Calculate intensity for each day
    activityMap.forEach((activity) => {
      const totalEvents = activity.suspiciousCount + activity.healthIssues;
      const hasOffline = activity.offlineCount > 0;
      const hasCriticalHealth = activity.events.some(
        (e) => e.type === 'health' && e.details.severity === 'critical',
      );

      if (hasCriticalHealth || activity.suspiciousCount > 5) {
        activity.intensity = 'critical';
      } else if (totalEvents > 3 || hasOffline) {
        activity.intensity = 'high';
      } else if (totalEvents > 1) {
        activity.intensity = 'medium';
      } else if (totalEvents > 0) {
        activity.intensity = 'low';
      }
    });

    return activityMap;
  }, [machines]);

  // Get calendar days for current month
  const getCalendarDays = () => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();

    const firstDay = new Date(year, month, 1);
    // const lastDay = new Date(year, month + 1, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());

    const days = [];
    const current = new Date(startDate);

    for (let i = 0; i < 42; i++) {
      // 6 weeks × 7 days
      days.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }

    return days;
  };

  const calendarDays = getCalendarDays();
  const selectedDateActivity = selectedDate
    ? heatMapData.get(selectedDate.toDateString())
    : null;

  const navigateMonth = (direction: 'prev' | 'next') => {
    setCurrentMonth((prev) => {
      const newDate = new Date(prev);
      newDate.setMonth(prev.getMonth() + (direction === 'next' ? 1 : -1));
      return newDate;
    });
  };

  const getIntensityClasses = (intensity: string) => {
    switch (intensity) {
      case 'low':
        return 'bg-yellow-100 hover:bg-yellow-200 border-yellow-200';
      case 'medium':
        return 'bg-orange-200 hover:bg-orange-300 border-orange-300';
      case 'high':
        return 'bg-red-200 hover:bg-red-300 border-red-300';
      case 'critical':
        return 'bg-red-500 hover:bg-red-600 text-white border-red-600';
      default:
        return 'bg-white hover:bg-gray-50 border-gray-200';
    }
  };

  const isCurrentMonth = (date: Date) => {
    return date.getMonth() === currentMonth.getMonth();
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const isSelected = (date: Date) => {
    return selectedDate?.toDateString() === date.toDateString();
  };

  return (
    <div className="flex h-full gap-8 p-6">
      {/* Calendar */}
      <div className="max-w-4xl flex-1">
        <Card className="h-full">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-2xl font-bold">
                {MONTHS[currentMonth.getMonth()]} {currentMonth.getFullYear()}
              </CardTitle>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigateMonth('prev')}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigateMonth('next')}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Weekday Headers */}
            <div className="mb-4 grid grid-cols-7 gap-2">
              {WEEKDAYS.map((day) => (
                <div
                  key={day}
                  className="py-2 text-center text-sm font-medium text-gray-500"
                >
                  {day}
                </div>
              ))}
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 gap-2">
              {calendarDays.map((date, index) => {
                const activity = heatMapData.get(date.toDateString());
                const intensityClasses = getIntensityClasses(
                  activity?.intensity || 'none',
                );

                return (
                  <button
                    key={index}
                    onClick={() => setSelectedDate(date)}
                    className={cn(
                      'group relative flex h-16 w-full flex-col items-center justify-center rounded-lg border-2 transition-all duration-200',
                      intensityClasses,
                      isSelected(date) && 'ring-2 ring-blue-500 ring-offset-2',
                      !isCurrentMonth(date) && 'opacity-40',
                      isToday(date) && 'ring-1 ring-blue-400',
                    )}
                  >
                    <span
                      className={cn(
                        'text-lg font-semibold',
                        !isCurrentMonth(date) && 'text-gray-400',
                        isToday(date) && 'text-blue-600',
                      )}
                    >
                      {date.getDate()}
                    </span>

                    {/* Activity Indicators */}
                    {activity && (
                      <div className="absolute top-1 right-1 flex gap-1">
                        {activity.suspiciousCount > 0 && (
                          <div className="flex h-2.5 w-2.5 items-center justify-center rounded-full bg-red-600">
                            <span className="text-[8px] font-bold text-white">
                              {activity.suspiciousCount > 9
                                ? '9+'
                                : activity.suspiciousCount}
                            </span>
                          </div>
                        )}
                        {activity.healthIssues > 0 && (
                          <div className="h-2.5 w-2.5 rounded-full bg-orange-500"></div>
                        )}
                      </div>
                    )}

                    {/* Tooltip on hover */}
                    {activity && (
                      <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 -translate-x-1/2 transform rounded bg-black px-2 py-1 text-xs whitespace-nowrap text-white opacity-0 transition-opacity group-hover:opacity-100">
                        {activity.suspiciousCount} suspicious,{' '}
                        {activity.healthIssues} health issues
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Legend */}
            <div className="mt-8 rounded-lg bg-gray-50 p-4">
              <h3 className="mb-3 text-lg font-semibold">Activity Legend</h3>
              <div className="flex flex-wrap gap-4">
                <div className="flex items-center gap-2">
                  <div className="h-6 w-6 rounded border-2 border-gray-200 bg-white"></div>
                  <span className="text-sm">No Activity</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-6 w-6 rounded border-2 border-yellow-200 bg-yellow-100"></div>
                  <span className="text-sm">Low Activity</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-6 w-6 rounded border-2 border-orange-300 bg-orange-200"></div>
                  <span className="text-sm">Medium Activity</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-6 w-6 rounded border-2 border-red-300 bg-red-200"></div>
                  <span className="text-sm">High Activity</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-6 w-6 rounded border-2 border-red-600 bg-red-500"></div>
                  <span className="text-sm text-white">Critical</span>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-6 border-t border-gray-200 pt-3">
                <div className="flex items-center gap-2">
                  <div className="h-2.5 w-2.5 rounded-full bg-red-600"></div>
                  <span className="text-sm">Suspicious Events</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-2.5 w-2.5 rounded-full bg-orange-500"></div>
                  <span className="text-sm">Health Issues</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Details Panel */}
      <div className="w-96">
        <Card className="h-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Activity className="h-6 w-6" />
              {selectedDate
                ? selectedDate.toLocaleDateString('en-US', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })
                : 'Select a Date'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedDateActivity ? (
              <div className="space-y-6">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center">
                    <div className="text-3xl font-bold text-red-600">
                      {selectedDateActivity.suspiciousCount}
                    </div>
                    <div className="text-sm font-medium text-red-500">
                      Suspicious Events
                    </div>
                  </div>
                  <div className="rounded-lg border border-orange-200 bg-orange-50 p-4 text-center">
                    <div className="text-3xl font-bold text-orange-600">
                      {selectedDateActivity.healthIssues}
                    </div>
                    <div className="text-sm font-medium text-orange-500">
                      Health Issues
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Event Details */}
                <div className="max-h-80 space-y-3 overflow-y-auto">
                  <h4 className="text-lg font-semibold">Event Timeline</h4>
                  {selectedDateActivity.events
                    .sort(
                      (a, b) =>
                        new Date(b.details.timestamp).getTime() -
                        new Date(a.details.timestamp).getTime(),
                    )
                    .map((event, index) => (
                      <div
                        key={index}
                        className="rounded-lg border p-3 transition-colors hover:bg-gray-50"
                      >
                        <div className="mb-2 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <MapPin className="h-4 w-4 text-gray-500" />
                            <span className="text-sm font-medium">
                              {event.machineName}
                            </span>
                          </div>
                          <Badge
                            variant={
                              event.type === 'suspicious'
                                ? 'destructive'
                                : 'secondary'
                            }
                            className="text-xs"
                          >
                            {event.type}
                          </Badge>
                        </div>

                        {event.type === 'suspicious' && (
                          <div className="space-y-1 text-xs text-gray-600">
                            <div>
                              Type:{' '}
                              <span className="font-medium">
                                {event.details.type.replace('_', ' ')}
                              </span>
                            </div>
                            <div>
                              Confidence:{' '}
                              <span className="font-medium">
                                {(event.details.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                            <div>
                              Time:{' '}
                              <span className="font-medium">
                                {new Date(
                                  event.details.timestamp,
                                ).toLocaleTimeString()}
                              </span>
                            </div>
                            {event.details.marked && (
                              <Badge variant="outline" className="mt-2">
                                {event.details.marked}
                              </Badge>
                            )}
                          </div>
                        )}

                        {event.type === 'health' && (
                          <div className="space-y-1 text-xs text-gray-600">
                            <div>
                              Issue:{' '}
                              <span className="font-medium">
                                {event.details.type.replace('_', ' ')}
                              </span>
                            </div>
                            <div>
                              Time:{' '}
                              <span className="font-medium">
                                {new Date(
                                  event.details.timestamp,
                                ).toLocaleTimeString()}
                              </span>
                            </div>
                            <Badge
                              variant={
                                event.details.severity === 'critical'
                                  ? 'destructive'
                                  : 'secondary'
                              }
                              className="mt-2"
                            >
                              {event.details.severity}
                            </Badge>
                          </div>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-gray-500">
                <Activity className="mx-auto mb-4 h-16 w-16 opacity-30" />
                <p className="text-lg font-medium">No activity recorded</p>
                <p className="text-sm">Select a date to view events</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
